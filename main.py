from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = FastAPI()

# CORS Middleware (для разработки можно разрешить все домены)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Параметры для Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_ID = '1GHbOD8qx4mUnLnh4yfTZEJUMx0WmNukCx6Zsl-n9cFs'
RANGE_NAME = 'Лист1!A:C'         # Диапазон для добавления данных (имя, отправитель, ссылка)
COUNT_CELL_RANGE = 'Лист1!H1'     # Ячейка для общего количества ссылок

# Аутентификация через сервисный аккаунт
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
sheets_service = build('sheets', 'v4', credentials=creds)

# Модель данных, получаемых с клиента
class LinkData(BaseModel):
    girlName: str
    senderName: str
    shareLink: str

@app.post("/generate_link")
async def generate_link(data: LinkData):
    # 1. Добавляем новую строку с данными
    values = [
        [data.girlName, data.senderName, data.shareLink]
    ]
    body = {
        'values': values
    }
    try:
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption='RAW',
            body=body
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении строки: {str(e)}")

    # 2. Чтение текущего значения общего счётчика из ячейки COUNT_CELL_RANGE
    try:
        current_count_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=COUNT_CELL_RANGE
        ).execute()
        values = current_count_result.get("values")
        if values and values[0]:
            try:
                current_count = int(values[0][0])
            except Exception:
                current_count = 0
        else:
            current_count = 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении счётчика: {str(e)}")

    # 3. Инкрементируем значение счётчика
    new_count = current_count + 1

    # 4. Обновляем ячейку с новым значением
    try:
        update_body = {
            'values': [[new_count]]
        }
        update_result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=COUNT_CELL_RANGE,
            valueInputOption='RAW',
            body=update_body
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении счётчика: {str(e)}")

    # 5. Возвращаем результат с обновлённым общим количеством ссылок
    return {
        "status": "success",
        "updatedRows": result.get("updates", {}).get("updatedRows", 0),
        "totalCount": new_count
    }

# Новый GET эндпоинт для получения общего количества сгенерированных ссылок
@app.get("/total_links")
async def total_links():
    try:
        current_count_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=COUNT_CELL_RANGE
        ).execute()
        values = current_count_result.get("values")
        if values and values[0]:
            try:
                current_count = int(values[0][0])
            except Exception:
                current_count = 0
        else:
            current_count = 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении счётчика: {str(e)}")
    return {"totalCount": current_count}
