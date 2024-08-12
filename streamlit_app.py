import pandas as pd
import streamlit as st
import plotly.express as px
import json
from pandas.api.types import is_string_dtype

st.title("Analyse des risques pour assurance")

# Téléchargement des fichiers
uploaded_files = {
    'inscription': st.file_uploader("Télécharger le fichier des inscriptions", type="xlsx"),
    'foyer': st.file_uploader("Télécharger le fichier des foyers", type="xlsx"),
    'individu': st.file_uploader("Télécharger le fichier des individus", type="xlsx"),
    'accident': st.file_uploader("Télécharger le fichier des accidents", type="xlsx")
}

# Vérification que tous les fichiers sont téléchargés
if all(uploaded_files.values()):
    # Chargement des données
    @st.cache_data
    def load_data(uploaded_files):
        dfs = {}
        for key, file in uploaded_files.items():
            dfs[key] = pd.read_excel(file)
            # Traiter les colonnes JSON si besoin
            for col in dfs[key].columns:
                if is_string_dtype(dfs[key][col]):
                    try:
                        dfs[key][col] = dfs[key][col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
                    except (json.JSONDecodeError, TypeError):
                        pass  # Ignorer si la colonne n'est pas JSON
        return dfs

    dfs = load_data(uploaded_files)

    # Extraire uniquement les 4 derniers chiffres des années de naissance
    for df in dfs.values():
        df['ANNEE DE NAISSANCE'] = df['ANNEE DE NAISSANCE'].astype(str).str[-4:]

    # Fréquence des accidents par type (regroupement des types peu fréquents)
    accident_types = dfs['accident']["De quel type d'accident s'agissait-il ?"].value_counts()
    other_threshold = accident_types.max() * 0.01  # Seuil de 1% du maximum pour regrouper les autres
    accident_types = accident_types.where(accident_types >= other_threshold, other='Autres')
    accident_types = accident_types.value_counts().reset_index(name='Nombre d\'accidents')
    accident_types.columns = ['Type d\'accident', 'Nombre d\'accidents']

    fig_accident_types = px.bar(accident_types, x='Type d\'accident', y='Nombre d\'accidents', 
                                title="Répartition des types d'accidents",
                                labels={'Type d\'accident': 'Type d\'accident', 'Nombre d\'accidents': 'Nombre d\'accidents'})
    fig_accident_types.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_accident_types)

    # Répartition des accidents par lieu (regroupement des lieux peu fréquents)
    accident_location_counts = dfs['accident']["Où a eu lieu l'accident ?"].value_counts()
    other_threshold_location = accident_location_counts.max() * 0.01  # Seuil de 1% du maximum pour regrouper les autres
    accident_location_counts = accident_location_counts.where(accident_location_counts >= other_threshold_location, other='Autres')
    accident_location_counts = accident_location_counts.value_counts().reset_index(name='Nombre d\'accidents')
    accident_location_counts.columns = ['Lieu de l\'accident', 'Nombre d\'accidents']

    fig_accident_location = px.pie(accident_location_counts, values='Nombre d\'accidents', names='Lieu de l\'accident', 
                                   title="Répartition des accidents par lieu")
    st.plotly_chart(fig_accident_location)

    # Spécification du format de date pour éviter l'avertissement
    dfs['accident']['Date'] = pd.to_datetime(dfs['accident']["À quelle date a eu lieu l'accident de la vie courante ?"], dayfirst=True)
    accidents_by_month = dfs['accident'].groupby(dfs['accident']['Date'].dt.to_period("M")).size().reset_index(name='Nombre d\'accidents')
    accidents_by_month['Date'] = accidents_by_month['Date'].dt.to_timestamp()

    fig_time = px.line(accidents_by_month, x='Date', y='Nombre d\'accidents', 
                       title="Évolution du nombre d'accidents au fil du temps",
                       labels={'Date': 'Date', 'Nombre d\'accidents': 'Nombre d\'accidents'})
    st.plotly_chart(fig_time)

else:
    st.warning("Veuillez télécharger tous les fichiers nécessaires pour commencer l'analyse.")
