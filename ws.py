import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def send_email(subject, body, to_email, attachment_path=None):
    # Configurações do servidor SMTP do Gmail
    smtp_server = "smtp.gmail.com"
    smtp_port = 465
    smtp_username = os.getenv('GMAIL_USERNAME')  # Substitua com a variável de ambiente do seu e-mail do Gmail
    smtp_password = os.getenv('GMAIL_PASSWORD')  # Substitua com a variável de ambiente da senha da sua conta do Gmail

    # Configurar a mensagem de e-mail
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = to_email
    msg['Subject'] = subject

    # Adicionar corpo do e-mail
    msg.attach(MIMEText(body, 'html'))

    # Adicionar anexo, se fornecido
    if attachment_path:
        with open(attachment_path, "rb") as attachment:
            part = MIMEApplication(attachment.read(), Name="resultado.csv")
            part['Content-Disposition'] = f'attachment; filename="{attachment_path}"'
            msg.attach(part)

    # Configurar conexão SMTP segura usando SSL
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, to_email, msg.as_string())

# URL da página para obter os preços
url = 'https://co.frubana.com/bog/Desechables/contenedores/contenedor-j2-darnel-unid'
headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"}

# Obtenha a página da web
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

# Data de execução do script
data_execucao = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')

# Nome do produto
prod_name = item_desc = soup.find('div', class_='productTitle').get_text().strip()

# Encontre todas as tags <div> com a classe "skuItemTiredDetails"
sku_details = soup.find_all("div", class_="skuItemTiredDetails")

# Crie listas vazias para armazenar os dados
min_quantity_list = []
unit_list = []
price_list = []

# Itere pelas tags encontradas
for item in sku_details:
    min_quantity = item.get("data-minquantity")
    unit = item.get("data-unit")

    # Use regex para extrair o preço (removendo caracteres não numéricos)
    price_data = item.get("data-saleprice")
    price = re.sub(r'[^\d.]', '', price_data)  # Remove caracteres não numéricos

    # Converta o preço em um número de ponto flutuante
    price = float(price)

    # Adicione os dados às listas
    min_quantity_list.append(str(min_quantity))  # Trate como texto
    unit_list.append(unit)
    price_list.append(price)

# Crie um DataFrame pandas com os dados
data = {
    'Nome do Produto': prod_name,
    'Min Quantity': min_quantity_list,
    'Unit': unit_list,
    'Price': price_list
}

df = pd.DataFrame(data)
# Adicione a coluna de "Data de Execução"
df['Data de execução'] = data_execucao

# Abra o arquivo CSV existente ou crie um novo se não existir
csv_file_path = 'https://raw.githubusercontent.com/afgneto89/WSSchedule/main/resultado.csv'
try:
    existing_df = pd.read_csv(csv_file_path)
except FileNotFoundError:
    df.to_csv(csv_file_path, index=False)
    existing_df = pd.read_csv(csv_file_path)

# Compare os preços com base na última data de execução para cada quantidade
new_rows = []  # Armazena as novas linhas a serem adicionadas
changed_prices = []  # Armazena as linhas com preços diferentes

# Compare os preços com base na última data de execução para cada quantidade
for index, row in df.iterrows():
    min_quantity = row['Min Quantity']
    price = row['Price']

    # Verifique se a quantidade já existe no arquivo CSV anterior
    if (existing_df['Min Quantity'] == min_quantity).any():
        last_execution_date = existing_df[existing_df['Min Quantity'] == min_quantity]['Data de execução'].max()
        last_price = existing_df[(existing_df['Min Quantity'] == min_quantity) & (
                    existing_df['Data de execução'] == last_execution_date)]['Price'].values[0]

        if price != last_price:
            # Atualize o preço somente se houver variação
            existing_df = pd.concat([existing_df, row.to_frame().T], ignore_index=True)
            changed_prices.append(row)

    else:
        # Adicione a nova linha se a quantidade e o preço não existirem no arquivo CSV
        if not (existing_df['Min Quantity'] == min_quantity).any() and not (existing_df['Price'] == price).any():
            existing_df = pd.concat([existing_df, row.to_frame().T], ignore_index=True)
            new_rows.append(row)

# Salve as alterações no arquivo CSV
existing_df.to_csv(csv_file_path, index=False, mode='w')

# Após o loop, envie o email apenas se houver novas linhas ou preços diferentes
if new_rows:
    email_subject = 'Novo(s) item(ns) adicionado(s) ao monitoramento'
    email_body = f"Olá, um novo item foi inserido para monitoramento dos preços.<br>Produto: {prod_name}<br>"
    for row in new_rows:
        email_body += f"<br>Min Quantity: {row['Min Quantity']}<br>Unit: {row['Unit']}<br>Price: {row['Price']}<br>"

    send_email(email_subject, email_body, os.getenv('DESTINATION_EMAIL'))  # Substitua com a variável de ambiente do e-mail de destino
    print("Sucesso ao enviar email de novas linhas")

if changed_prices:
    email_subject = 'Preços foram alterados na planilha'
    email_body = "Preços foram alterados:<br>"
    for row in changed_prices:
        email_body += f"Min Quantity: {row['Min Quantity']}, Price: {row['Price']}<br>"

    send_email(email_subject, email_body, os.getenv('DESTINATION_EMAIL'))  # Substitua com a variável de ambiente do e-mail de destino
    print("Sucesso ao enviar email de preços alterados")

print(new_rows)
print(changed_prices)
