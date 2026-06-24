"""Gmail SMTP でレポートPDFを送信するモジュール。
.env の SENDER_EMAIL / SENDER_APP_PASSWORD を設定するだけで動作する。
"""
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def is_configured() -> bool:
    """送信設定が完了しているか確認。"""
    return bool(os.getenv("SENDER_EMAIL")) and bool(os.getenv("SENDER_APP_PASSWORD"))


def send_report(
    to_email: str,
    subject: str,
    body: str,
    pdf_bytes: bytes,
    pdf_filename: str,
) -> tuple[bool, str]:
    """PDFを添付してメール送信。(成功: True, "") / (失敗: False, エラー文) を返す。"""
    sender_email = os.getenv("SENDER_EMAIL", "").strip()
    app_password = os.getenv("SENDER_APP_PASSWORD", "").strip()

    if not sender_email or not app_password:
        return False, (
            "メール設定が未完了です。\n"
            ".env ファイルの SENDER_EMAIL と SENDER_APP_PASSWORD を設定してください。"
        )

    msg = MIMEMultipart()
    msg["From"] = f"LIFE DESIGN LAB トドク <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
    msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, to_email, msg.as_bytes())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, (
            "認証エラー: メールアドレスまたはアプリパスワードが正しくありません。\n"
            "Googleアカウント → セキュリティ → アプリパスワード で16桁のパスワードを確認してください。"
        )
    except smtplib.SMTPRecipientsRefused:
        return False, f"送信先アドレスが拒否されました: {to_email}"
    except TimeoutError:
        return False, "タイムアウト: ネットワーク接続を確認してください。"
    except Exception as e:
        return False, f"送信エラー: {e}"
