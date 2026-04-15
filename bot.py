import time
import smtplib
from email.message import EmailMessage
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import os
from cv_tailor import cv_olustur

# --- AYARLAR ---
ARAMA_LISTESI = [
    "Data Curation", "Bounding Box", "Search Evaluation", "Model Evaluation",
    "Prompt Engineering", "Data Labeling", "Veri Etiketleme", "Image Annotation",
    "Computer Vision", "Görüntü İşleme", "Nesne Tespiti", "Object Detection",
    "Veri girişi", "Data review", "Web Scraping", "Workflow Automation",
    "Computer Vision Intern", "Veri Giriş Uzmanı (AI)"
]

EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')
ALICI_POSTA = EMAIL_USER

# Kaç ilan için CV üretilsin? (fazla = fazla API maliyeti)
# Örn: 3 → günde en fazla 3 ilan için CV üretir, geri kalanlar sadece link olarak gelir
MAX_CV_URET = 3


def ilan_metnini_cek(driver, url: str) -> str:
    """İlan sayfasını açar, iş tanımı metnini çeker."""
    try:
        driver.get(url)
        time.sleep(3)
        # LinkedIn iş tanımı genellikle bu class'ta
        selectors = [
            "show-more-less-html__markup",
            "description__text",
            "jobs-description__content"
        ]
        for selector in selectors:
            try:
                element = driver.find_element(By.CLASS_NAME, selector)
                metin = element.text.strip()
                if metin and len(metin) > 100:
                    return metin[:3000]  # Claude'a çok uzun gönderme
            except Exception:
                continue
        return ""
    except Exception as e:
        print(f"İlan metni çekilemedi: {e}")
        return ""


def ilan_tara(driver) -> list:
    """İlanları tarar, link + başlık bilgisiyle döner."""
    tum_ilanlar = []

    for kelime in ARAMA_LISTESI:
        url = f"https://www.linkedin.com/jobs/search/?keywords={kelime.replace(' ', '%20')}&location=Turkey&f_TPR=r86400"
        driver.get(url)
        time.sleep(3)

        ilanlar = driver.find_elements(By.CLASS_NAME, "base-card__full-link")
        for ilan in ilanlar[:3]:
            href = ilan.get_attribute('href')
            baslik = ilan.text.strip() or kelime
            tum_ilanlar.append({
                "anahtar_kelime": kelime,
                "baslik": baslik,
                "url": href
            })

    return tum_ilanlar


def mail_at(ilan_listesi: list, pdf_dosyalari: list):
    """İlan listesini ve PDF'leri email ile gönderir."""
    if not ilan_listesi:
        print("Bugün yeni ilan yok.")
        return

    # Email içeriği
    ilan_satirlari = []
    for i, ilan in enumerate(ilan_listesi, 1):
        ilan_satirlari.append(f"{i}. [{ilan['anahtar_kelime']}] {ilan['baslik']}\n   {ilan['url']}")

    email_metni = f"""Bugün {len(ilan_listesi)} ilan bulundu.

{'='*50}
TÜM İLANLAR:
{'='*50}

{chr(10).join(ilan_satirlari)}

{'='*50}
CV'ler ekte — ilk {len(pdf_dosyalari)} ilan için özelleştirildi.
"""

    # MIME ile email oluştur (attachment için)
    msg = MIMEMultipart()
    msg['Subject'] = f"🎯 Kalk İş Var! — {len(ilan_listesi)} Yeni İlan + {len(pdf_dosyalari)} Özel CV"
    msg['From'] = EMAIL_USER
    msg['To'] = ALICI_POSTA
    msg.attach(MIMEText(email_metni, 'plain', 'utf-8'))

    # PDF'leri ekle
    for pdf_yolu in pdf_dosyalari:
        if os.path.exists(pdf_yolu):
            with open(pdf_yolu, 'rb') as f:
                pdf_verisi = f.read()
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(pdf_verisi)
            encoders.encode_base64(part)
            dosya_adi = os.path.basename(pdf_yolu)
            part.add_header('Content-Disposition', f'attachment; filename="{dosya_adi}"')
            msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

    print(f"✅ {len(ilan_listesi)} ilan + {len(pdf_dosyalari)} CV emaile gönderildi!")


# --- ANA AKIŞ ---
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

print("📡 İlanlar taranıyor...")
ilanlar = ilan_tara(driver)
print(f"   {len(ilanlar)} ilan bulundu.")

# En iyi ilanlara özel CV üret
pdf_dosyalari = []
cv_uretilen = 0

print(f"🤖 İlk {MAX_CV_URET} ilan için CV hazırlanıyor...")
for ilan in ilanlar:
    if cv_uretilen >= MAX_CV_URET:
        break
    try:
        print(f"   CV hazırlanıyor: {ilan['baslik'][:50]}...")
        metin = ilan_metnini_cek(driver, ilan['url'])
        if not metin:
            print(f"   ⚠️ İlan metni alınamadı, atlandı.")
            continue
        pdf_yolu = cv_olustur(metin, ilan['baslik'])
        pdf_dosyalari.append(pdf_yolu)
        cv_uretilen += 1
        print(f"   ✅ PDF oluşturuldu: {os.path.basename(pdf_yolu)}")
        time.sleep(2)  # API rate limit için
    except Exception as e:
        print(f"   ❌ CV üretim hatası: {e}")

driver.quit()

mail_at(ilanlar, pdf_dosyalari)
