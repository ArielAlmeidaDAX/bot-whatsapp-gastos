from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

app = Flask(__name__)

# Credenciais Twilio
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

# Credenciais Google Sheets
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    gsh = gspread.authorize(creds)
    sheet = gsh.open_by_key(os.environ.get('GOOGLE_SHEET_ID')).sheet1
except:
    sheet = None

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    msg_body = request.form.get('Body', '').strip()
    sender = request.form.get('From', '')
    
    # Processar mensagem
    if msg_body.lower() == 'relatorio':
        resposta = gerar_relatorio()
    elif msg_body.lower() == 'ajuda':
        resposta = 'Comandos:\n1. "Categoria Valor" - Registra gasto\n2. "relatorio" - Mostra resumo\n3. "ajuda" - Mostra este menu'
    else:
        resposta = registrar_gasto(msg_body)
    
    # Responder
    resp = MessagingResponse()
    resp.message(resposta)
    return str(resp)

def registrar_gasto(msg):
    try:
        partes = msg.rsplit(' ', 1)
        if len(partes) != 2:
            raise ValueError('Formato invalido')
        categoria, valor = partes[0], partes[1]
        try:
            float(valor)
        except:
            raise ValueError('Valor invalido')
        
        if sheet:
            data = datetime.now().strftime('%d/%m/%Y')
            sheet.append_row([data, categoria, valor])
            resposta = f'Gasto registrado!\nCategoria: {categoria}\nValor: R$ {valor}'
        else:
            resposta = f'Gasto: {categoria} - R$ {valor} (banco de dados indisponivel)'
        return resposta
    except:
        return 'Formato invalido. Use: Categoria Valor\nEx: Padaria 12.50'

def gerar_relatorio():
    try:
        if not sheet:
            return 'Banco de dados indisponivel'
        
        todos_dados = sheet.get_all_values()[1:]
        total = 0
        categorias = {}
        
        for linha in todos_dados:
            if len(linha) >= 3:
                try:
                    categoria, valor = linha[1], float(linha[2])
                    total += valor
                    categorias[categoria] = categorias.get(categoria, 0) + valor
                except:
                    pass
        
        relatorio = 'RELATORIO DO DIA\n'
        relatorio += '=' * 30 + '\n'
        for cat, val in sorted(categorias.items()):
            relatorio += f'{cat}: R$ {val:.2f}\n'
        relatorio += '=' * 30 + '\n'
        relatorio += f'TOTAL: R$ {total:.2f}'
        return relatorio
    except Exception as e:
        return f'Erro ao gerar relatorio: {str(e)}'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
