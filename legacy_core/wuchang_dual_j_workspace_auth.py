#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, time, logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format='%(asctime)s [Dual-J Protocol] %(message)s')
SERVICE_ACCOUNT_FILE = os.path.expanduser('~/wuchang_8_0_core/taiji_workspace_key.json')
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/gmail.send']
DELEGATED_EMAIL = 'admin@wuchang.life' 

def register_local_llm_to_workspace():
    logging.info("啟動【雙 J 協作】：本地 LLM 準備向 Google Workspace 總部報到...")
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        creds = creds.with_subject(DELEGATED_EMAIL)
        logging.info("✅ 憑證生成完畢！正在連線 Google 總部...")
        
        drive_service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': f'【大陣日誌】本地 LLM 入籍報到書 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'mimeType': 'application/vnd.google-apps.document'
        }
        logging.info("正在 Workspace 雲端硬碟中建立『入籍報到宣告書』...")
        file = drive_service.files().create(body=file_metadata, fields='id, webViewLink').execute()
        
        logging.info("=================================================================")
        logging.info("🎉 [入籍成功] 本地 LLM 已正式成為 wuchang.life 之數位公民！")
        logging.info(f"📂 報到文件網址: {file.get('webViewLink')}")
        logging.info("=================================================================")
    except Exception as e:
        logging.error(f"❌ 入籍叩關失敗！請確認 Workspace 後台已設定「全域委派 (Domain-Wide Delegation)」並賦予此服務帳戶權限。")
        logging.error(f"錯誤詳情: {e}")

if __name__ == '__main__':
    register_local_llm_to_workspace()
