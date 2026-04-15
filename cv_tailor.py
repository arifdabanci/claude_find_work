import anthropic
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors

# Master CV - botun her zaman bu CV'yi base olarak kullanır
MASTER_CV = open(os.path.join(os.path.dirname(__file__), "master_cv.txt"), encoding="utf-8").read()

def cv_olustur(ilan_metni: str, ilan_basligi: str = "pozisyon") -> str:
    """
    İlan metnini alır, Claude API ile CV'yi özelleştirir,
    PDF kaydeder ve dosya yolunu döner.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""Sen profesyonel bir teknik işe alım uzmanısın ve CV optimizasyon konusunda uzmansın.

Aşağıda bir iş ilanı ve adayın master CV'si var.

Görevin:
1. İlandaki en kritik 5-7 teknik anahtar kelimeyi tespit et
2. Adayın mevcut deneyimlerini (Teknofest projeleri, Python botları, AI annotation tecrübesi, Etsy operasyonları) bu anahtar kelimelerle yeniden ifade et
3. Professional Summary ve Core Competencies bölümlerini ilana özel yeniden yaz
4. Diğer bölümleri (iş deneyimi, projeler) ilana en uygun sırayla ve kelimelerle düzenle
5. ASLA yalan söyleme, olmayan bir deneyim ekleme - sadece mevcut deneyimleri ilana uygun terimlerle ifade et
6. ATS uyumlu kal: basit metin, bullet point'ler, net başlıklar

KURAL: Çıktı direkt CV metni olsun. Açıklama, yorum veya "İşte CV'niz:" gibi giriş cümleleri OLMASIN.
Format olarak master CV'nin yapısını koru (büyük başlıklar, bullet'lar vs.)

---
İŞ İLANI:
{ilan_metni}

---
MASTER CV:
{MASTER_CV}
"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    cv_metni = message.content[0].text
    pdf_yolu = pdf_olustur(cv_metni, ilan_basligi)
    return pdf_yolu


def pdf_olustur(cv_metni: str, ilan_basligi: str) -> str:
    """CV metnini ATS dostu PDF'e dönüştürür."""

    # Dosya adını temizle
    temiz_baslik = re.sub(r'[^\w\s-]', '', ilan_basligi)[:40].strip().replace(' ', '_')
    dosya_adi = f"CV_Arif_{temiz_baslik}.pdf"
    dosya_yolu = os.path.join(os.path.dirname(__file__), dosya_adi)

    doc = SimpleDocTemplate(
        dosya_yolu,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # Özel stiller
    isim_stili = ParagraphStyle(
        'Isim',
        parent=styles['Normal'],
        fontSize=16,
        fontName='Helvetica-Bold',
        spaceAfter=4,
        textColor=colors.black
    )
    baslik_stili = ParagraphStyle(
        'Baslik',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.black,
        borderPadding=(0, 0, 2, 0)
    )
    normal_stili = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        spaceAfter=2,
        leading=13
    )
    bullet_stili = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        leftIndent=12,
        spaceAfter=2,
        leading=13
    )

    story = []
    satirlar = cv_metni.split('\n')

    for satir in satirlar:
        satir = satir.strip()
        if not satir:
            story.append(Spacer(1, 4))
            continue

        # İsim satırı (ilk büyük harf satırı)
        if satir.isupper() and len(satir) > 10 and story == []:
            story.append(Paragraph(satir, isim_stili))

        # Büyük harf başlıklar (bölüm başlıkları)
        elif satir.isupper() and len(satir) > 3:
            story.append(Spacer(1, 6))
            story.append(Paragraph(satir, baslik_stili))
            # Başlık altına çizgi etkisi için bir spacer
            story.append(Spacer(1, 2))

        # Bullet point'ler
        elif satir.startswith('- ') or satir.startswith('* '):
            temiz = satir[2:]
            story.append(Paragraph(f"• {temiz}", bullet_stili))

        # Normal metin
        else:
            story.append(Paragraph(satir, normal_stili))

    doc.build(story)
    return dosya_yolu
