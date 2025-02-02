import streamlit as st
from fpdf import FPDF
import math
import requests
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import pytz

# --- Création d'une classe PDF personnalisée ---
class PDF(FPDF):
    def header(self):
        # Titre centré avec une police en gras
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Weather-Shield', ln=True, align='C')
        # Ligne horizontale sous le titre
        self.set_line_width(0.5)
        self.line(10, 20, 200, 20)
        self.ln(10)
        
    def footer(self):
        # Positionnement à 1.5 cm du bas
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        # Affichage de la date du jour à Nice dans le pied de page
        nice_tz = pytz.timezone("Europe/Paris")
        date_nice = datetime.datetime.now(nice_tz).strftime("%d/%m/%Y")
        self.cell(0, 10, f"Date du jour à Nice : {date_nice} - Page {self.page_no()}", 0, 0, 'C')

# --- Fonctions de base ---
def calcul_chiffre_affaire(pl_t, CA, pl_pivot):
    if pl_t >= pl_pivot:
        return 0
    elif 0 < pl_t < pl_pivot:
        return ((pl_pivot - pl_t) / pl_pivot) * CA
    else:
        return CA

def calcul_resultat(pl_t, CA, C_f, pl_pivot):
    if isinstance(pl_t, (int, float)):
        CA_t = calcul_chiffre_affaire(pl_t, CA, pl_pivot)
        return CA_t - C_f
    else:
        st.write(f"Erreur : Valeur inattendue de pl_t : {pl_t}")
        return 0

def obtenir_donnees_historique_open_meteo(ville, start_date, end_date):
    API_KEY = "1eb78358d0332a01b472417af647fef7"
    url_geo = f"http://api.openweathermap.org/geo/1.0/direct?q={ville}&limit=1&appid={API_KEY}"
    response_geo = requests.get(url_geo).json()

    if not response_geo:
        st.error("🚨 Impossible de récupérer les coordonnées GPS de la ville.")
        return []

    lat, lon = response_geo[0]["lat"], response_geo[0]["lon"]
    url_meteo = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=precipitation_sum&timezone=Europe/Paris"
    response_meteo = requests.get(url_meteo).json()

    if "daily" not in response_meteo or "precipitation_sum" not in response_meteo["daily"]:
        st.error("🚨 Impossible de récupérer les données météorologiques.")
        return []

    return [float(x) if x is not None else 0.0 for x in response_meteo["daily"]["precipitation_sum"]]

def calcul_prime_annuelle(ville, CA, C_f, pl_pivot, start_date, end_date):
    niveaux_pluie = obtenir_donnees_historique_open_meteo(ville, start_date, end_date)
    
    if not niveaux_pluie:
        return 0
    
    resultats_journaliers = [calcul_resultat(pl, CA, C_f, pl_pivot) for pl in niveaux_pluie]
    pertes_moyennes = sum(abs(res) for res in resultats_journaliers if res < 0) / len(niveaux_pluie)
    
    facteur_securite = 1.2
    prime_annuelle = pertes_moyennes * 365 * facteur_securite
    return prime_annuelle

# --- Configuration de la page et barre latérale ---
st.set_page_config(page_title="Weather-Shield", page_icon="☂️", layout="wide")
st.markdown(
    """
    <style>
    .main {background-color: #F0F2F6;}
    .sidebar .sidebar-content {background-color: #E3F2FD;}
    .stButton>button {
        background-color: #1976D2;
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 4px;
        cursor: pointer;
    }
    .stButton>button:hover {background-color: #1565C0;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("🌈 Paramètres")
ville = st.sidebar.text_input("🏙️ Ville :", value="Paris")
CA = st.sidebar.number_input("💰 Chiffre d'affaires max/jour (€) :", min_value=0.0, value=1000.0)
C_f = st.sidebar.number_input("📉 Coûts fixes/jour (€) :", min_value=0.0, value=300.0)
pl_pivot = st.sidebar.number_input("🌧️ Pluie pivot (mm) :", min_value=0.0, value=10.0)
start_date = st.sidebar.date_input("📅 Date de début", datetime.date.today().replace(year=datetime.date.today().year - 10))
end_date = st.sidebar.date_input("📅 Date de fin", datetime.date.today())

# --- Contenu principal ---
st.title("☂️ Weather-Shield : Assurance Météorologique")
st.markdown("**Prévision et calcul de votre prime d'assurance** en fonction des données de pluviométrie historiques.")

if start_date > end_date:
    st.error("🚨 La date de début doit être antérieure à la date de fin.")
else:
    # Calcul de la prime annuelle
    prime_annuelle = calcul_prime_annuelle(ville, CA, C_f, pl_pivot, start_date, end_date)
    st.success(f"💶 Prime d'assurance estimée pour un an : {prime_annuelle:.2f} EUR")
    
    # --- Génération du devis PDF avec tableau ---
    pdf_devis = PDF()
    pdf_devis.add_page()
    pdf_devis.set_font("Arial", size=12)
    pdf_devis.cell(100, 10, txt="Chiffre d'affaires max :", border=0)
    pdf_devis.cell(90, 10, txt=f"{CA} EUR", border=0, ln=1)
    pdf_devis.cell(100, 10, txt="Coûts fixes :", border=0)
    pdf_devis.cell(90, 10, txt=f"{C_f} EUR", border=0, ln=1)
    pdf_devis.cell(100, 10, txt="Pluie pivot :", border=0)
    pdf_devis.cell(90, 10, txt=f"{pl_pivot} mm", border=0, ln=1)
    pdf_devis.cell(100, 10, txt="Prime estimée :", border=0)
    pdf_devis.cell(90, 10, txt=f"{prime_annuelle:.2f} EUR", border=0, ln=1)
    pdf_devis.ln(10)
    pdf_devis.output("devis_assurance.pdf")
    
    with open("devis_assurance.pdf", "rb") as file:
        st.download_button(
            label="📄 Télécharger le devis en PDF",
            data=file,
            file_name="devis_assurance.pdf",
            mime="application/pdf",
        )
    
    # --- Récupération des données pour l'analyse rétrospective ---
    niveaux_pluie = obtenir_donnees_historique_open_meteo(ville, start_date, end_date)
    if niveaux_pluie:
        dates = pd.date_range(start=start_date, end=end_date).strftime('%d/%m/%Y').tolist()
        resultats_journaliers = [calcul_resultat(pl, CA, C_f, pl_pivot) for pl in niveaux_pluie]
        resultats_assures = [max(res, 0) for res in resultats_journaliers]
        
        df = pd.DataFrame({
            "Date": dates,
            "Pluviométrie (mm)": niveaux_pluie,
            "Résultat sans assurance (€)": resultats_journaliers,
            "Résultat avec assurance (€)": resultats_assures
        })
        st.dataframe(df)
        
        total_sans_assurance = sum(resultats_journaliers)
        total_avec_assurance = sum(resultats_assures)
        impact = total_avec_assurance - total_sans_assurance
        impact_percent = (impact / abs(total_sans_assurance)) * 100 if total_sans_assurance != 0 else 0
        
        st.subheader("📊 Analyse rétrospective")
        st.markdown("Cette analyse compare les résultats financiers avec et sans assurance sur la période sélectionnée. L'**impact** indique la différence en pourcentage, vous montrant si la couverture aurait amélioré votre situation financière.")
        st.write(f"🔹 **Total sans assurance :** {total_sans_assurance:.2f} EUR")
        st.write(f"🔹 **Total avec assurance :** {total_avec_assurance:.2f} EUR")
        st.write(f"📊 **Impact de l'assurance :** {impact_percent:.2f}%")
        
        # Graphique comparatif
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df["Date"], df["Résultat sans assurance (€)"], label="Sans assurance", color='red', alpha=0.6, marker='o')
        ax.plot(df["Date"], df["Résultat avec assurance (€)"], label="Avec assurance", color='green', alpha=0.6, marker='o')
        ax.set_xlabel("Date")
        ax.set_ylabel("Résultat (€)")
        ax.set_title("Comparaison des résultats journaliers")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.5)
        interval = max(1, len(df) // 10)
        ax.set_xticks(range(0, len(df), interval))
        ax.set_xticklabels(df["Date"][::interval], rotation=45, ha="right")
        st.pyplot(fig)
        
        # Génération du PDF pour l'analyse rétrospective avec tableau et explications
        pdf_retro = PDF()
        pdf_retro.add_page()
        pdf_retro.set_font("Arial", size=12)
        pdf_retro.cell(100, 10, txt="Prime estimée :", border=0)
        pdf_retro.cell(90, 10, txt=f"{prime_annuelle:.2f} EUR", border=0, ln=1)
        pdf_retro.cell(100, 10, txt="Impact de l'assurance :", border=0)
        pdf_retro.cell(90, 10, txt=f"{impact_percent:.2f}%", border=0, ln=1)
        conclusion_text = "Assurance bénéfique" if impact_percent > 0 else "Assurance non nécessaire"
        pdf_retro.cell(100, 10, txt="Conclusion :", border=0)
        pdf_retro.cell(90, 10, txt=conclusion_text, border=0, ln=1)
        pdf_retro.ln(10)
        pdf_retro.cell(200, 10, txt="(Les valeurs ci-dessus sont basées sur l'analyse historique de la pluviométrie.)", ln=True, align="C")
        pdf_retro.output("analyse_retrospective.pdf")
        
        with open("analyse_retrospective.pdf", "rb") as file:
            st.download_button(
                label="📄 Télécharger l'analyse rétrospective en PDF",
                data=file,
                file_name="analyse_retrospective.pdf",
                mime="application/pdf",
            )
