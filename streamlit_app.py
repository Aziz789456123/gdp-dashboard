import streamlit as st
import pandas as pd
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

    # Calcul des taux de participation
    total_volontaires = len(dfs['inscription'])
    volontaires_inscrits = total_volontaires
    volontaires_foyer = dfs['foyer']['VOLONTAIRE N°'].nunique()
    volontaires_individus = dfs['individu']['VOLONTAIRE N°'].nunique()
    volontaires_accidents = dfs['accident']['VOLONTAIRE N°'].nunique()

    taux_participation_inscription = (volontaires_inscrits / total_volontaires) * 100
    taux_participation_reponses_regulieres = ((volontaires_foyer + volontaires_individus) / (2 * total_volontaires)) * 100
    taux_participation_accidents = (volontaires_accidents / total_volontaires) * 100

    # Onglets pour les différentes catégories d'analyses
    tab1, tab2, tab3, tab4 = st.tabs(["Suivi des volontaires", "Données des volontaires", "Données des accidents", "Facteurs de risques"])

    # 1. Suivi des volontaires
    with tab1:
        st.header("1. Suivi des volontaires")
        
        st.subheader("Taux de participation continue")
        st.write(f"Taux de participation continue à l'inscription: {taux_participation_inscription:.2f}%")
        st.write(f"Taux de participation continue aux réponses régulières: {taux_participation_reponses_regulieres:.2f}%")
        st.write(f"Taux de participation continue aux déclarations d'accidents: {taux_participation_accidents:.2f}%")

        dfs['inscription']['DATE DE REMPLISSAGE'] = pd.to_datetime(dfs['inscription']['DATE DE REMPLISSAGE'])
        inscriptions_par_mois = dfs['inscription'].groupby(dfs['inscription']['DATE DE REMPLISSAGE'].dt.to_period("M")).size().reset_index(name='Nombre d\'inscriptions')
        inscriptions_par_mois['DATE DE REMPLISSAGE'] = inscriptions_par_mois['DATE DE REMPLISSAGE'].dt.to_timestamp()

        fig_inscriptions = px.line(inscriptions_par_mois, x='DATE DE REMPLISSAGE', y='Nombre d\'inscriptions', 
                                   title="Nombre de nouvelles inscriptions par mois")
        st.plotly_chart(fig_inscriptions)

    # 2. Données des volontaires
    with tab2:
        st.header("2. Données des volontaires")

        # Répartition par sexe (camembert interactif)
        sexe_counts = dfs['individu']["GENRE"].value_counts().reset_index()
        sexe_counts.columns = ['Sexe', 'Nombre']
        fig_sexe = px.pie(sexe_counts, values='Nombre', names='Sexe', 
                          title="Répartition des assurés par sexe")
        st.plotly_chart(fig_sexe)

        # Répartition par genre (camembert interactif)
        genre_counts = dfs['individu']["Vous êtes :"].value_counts().reset_index()
        genre_counts.columns = ['Genre', 'Nombre']
        fig_genre = px.pie(genre_counts, values='Nombre', names='Genre', 
                           title="Répartition des assurés par genre")
        st.plotly_chart(fig_genre)

        # Répartition par niveau d'éducation (trié par ordre décroissant)
        education_counts = dfs['individu']["Quel est le diplôme le plus élevé que vous avez obtenu ?"].value_counts().sort_values(ascending=False).reset_index()
        education_counts.columns = ['Niveau d\'éducation', 'Nombre']
        fig_education = px.bar(education_counts, x='Niveau d\'éducation', y='Nombre',
                               title="Répartition des assurés par niveau d'éducation",
                               labels={'Niveau d\'éducation': 'Niveau d\'éducation', 'Nombre': 'Nombre de personnes'})
        st.plotly_chart(fig_education)

        # Répartition par pratique d'activité physique (camembert interactif)
        activity_counts = dfs['individu']["Avez-vous pratiqué une activité physique ou sportive au cours des 12 derniers mois ? "].value_counts().reset_index()
        activity_counts.columns = ['Pratique d\'activité physique', 'Nombre']
        fig_activity = px.pie(activity_counts, values='Nombre', names='Pratique d\'activité physique', 
                              title="Répartition des assurés par pratique d'activité physique")
        st.plotly_chart(fig_activity)

        # Répartition par tranches d'âge (camembert interactif)
        bins = [0, 18, 30, 45, 60, 75, 90, 100]
        labels = ["0-18", "19-30", "31-45", "46-60", "61-75", "76-90", "91+"]
        dfs['individu']['Tranche d\'âge'] = pd.cut(pd.to_numeric(dfs['individu']['ANNEE DE NAISSANCE']), bins=bins, labels=labels, right=False)
        age_counts = dfs['individu']['Tranche d\'âge'].value_counts().reset_index()
        age_counts.columns = ['Tranche d\'âge', 'Nombre']
        fig_age = px.pie(age_counts, values='Nombre', names='Tranche d\'âge',
                         title="Répartition des assurés par tranches d'âge")
        st.plotly_chart(fig_age)

        # Analyse de l'IMC (avec correction des valeurs aberrantes)
        dfs['individu']['IMC'] = dfs['individu']["Quel est votre poids actuel en kg ?"] / (dfs['individu']["Quelle est votre taille actuelle en cm ?"] / 100) ** 2
        dfs['individu'] = dfs['individu'][dfs['individu']['IMC'] < 60]  # Suppression des valeurs aberrantes
        fig_imc = px.histogram(dfs['individu'], x="IMC", 
                               title="Répartition de l'IMC des assurés",
                               labels={'IMC': 'Indice de Masse Corporelle (IMC)'})
        st.plotly_chart(fig_imc)

    # 3. Données des accidents
    with tab3:
        st.header("3. Données des accidents")

        # Fréquence des accidents par type (regroupement des types peu fréquents)
        accident_types = dfs['accident']["De quel type d'accident s'agissait-il ?"].value_counts()
        other_threshold = accident_types.max() * 0.01  # Seuil de 1% du maximum pour regrouper les autres
        accident_types = accident_types.where(accident_types >= other_threshold, other='Autres').value_counts().reset_index()
        accident_types.columns = ['Type d\'accident', 'Nombre d\'accidents']
        fig_accident_types = px.bar(accident_types, x='Type d\'accident', y='Nombre d\'accidents', 
                                    title="Répartition des types d'accidents",
                                    labels={'Type d\'accident': 'Type d\'accident', 'Nombre d\'accidents': 'Nombre d\'accidents'})
        fig_accident_types.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_accident_types)

        # Gravité des accidents (basée sur l'hospitalisation)
        dfs['accident']['Gravité'] = dfs['accident']
        # Gravité des accidents (basée sur l'hospitalisation)
        dfs['accident']['Gravité'] = dfs['accident']["Combien de jours avez-vous été hospitalisé(e) ?"].apply(
            lambda x: "Grave" if x > 0 else "Léger")
        fig_gravity = px.histogram(dfs['accident'], x="De quel type d'accident s'agissait-il ?", color="Gravité",
                                   title="Gravité des accidents par type",
                                   labels={'De quel type d\'accident s\'agissait-il ?': 'Type d\'accident', 'Gravité': 'Gravité'})
        fig_gravity.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_gravity)

        # Répartition des accidents par lieu (regroupement des lieux peu fréquents)
        accident_location_counts = dfs['accident']["Où a eu lieu l'accident ?"].value_counts()
        other_threshold_location = accident_location_counts.max() * 0.01  # Seuil de 1% du maximum pour regrouper les autres
        accident_location_counts = accident_location_counts.where(accident_location_counts >= other_threshold_location, other='Autres').value_counts().reset_index()
        accident_location_counts.columns = ['Lieu de l\'accident', 'Nombre']
        fig_accident_location = px.pie(accident_location_counts, values='Nombre', names='Lieu de l\'accident', 
                                       title="Répartition des accidents par lieu")
        st.plotly_chart(fig_accident_location)

        # Évolution du nombre d'accidents au fil du temps
        dfs['accident']['Date'] = pd.to_datetime(dfs['accident']["À quelle date a eu lieu l'accident de la vie courante ?"])
        accidents_by_month = dfs['accident'].groupby(dfs['accident']['Date'].dt.to_period("M")).size().reset_index(name='Nombre d\'accidents')
        accidents_by_month['Date'] = accidents_by_month['Date'].dt.to_timestamp()

        fig_time = px.line(accidents_by_month, x='Date', y='Nombre d\'accidents', 
                           title="Évolution du nombre d'accidents au fil du temps",
                           labels={'Date': 'Date', 'Nombre d\'accidents': 'Nombre d\'accidents'})
        st.plotly_chart(fig_time)

    # 4. Facteurs de risques
    with tab4:
        st.header("4. Facteurs de risques")

        # Relation entre l'IMC et les accidents
        fig_imc_accidents = px.scatter(dfs['individu'], x="IMC", y="Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?",
                             title="Relation entre IMC et occurrence d'accidents",
                             labels={'IMC': 'Indice de Masse Corporelle (IMC)', 'Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?': 'Accidents'})
        st.plotly_chart(fig_imc_accidents)

        # Relation entre la consommation d'alcool et les accidents
        alcohol_mapping = {
            "Jamais": 0,
            "Une fois par mois ou moins": 1,
            "2 à 4 fois par mois": 2,
            "2 à 3 fois par semaine": 3,
            "4 fois ou plus par semaine": 4
        }
        dfs['individu']['Consommation alcool'] = dfs['individu']["A quelle fréquence consommez-vous de l'alcool (Vin, bière, cidre, apéritif, digestif, …) ?"].map(alcohol_mapping)

        fig_alcohol = px.box(dfs['individu'], x="Consommation alcool", y="Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?",
                             title="Relation entre consommation d'alcool et occurrence d'accidents",
                             labels={'Consommation alcool': 'Fréquence de consommation d\'alcool', 'Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?': 'Accidents'})
        st.plotly_chart(fig_alcohol)

        # Relation entre le type de logement et les accidents
        housing_accidents = pd.merge(dfs['foyer'], dfs['accident'], on="VOLONTAIRE N°")
        fig_housing = px.histogram(housing_accidents, x="Vous habitez dans :", color="De quel type d'accident s'agissait-il ?",
                                   title="Types d'accidents selon le type de logement",
                                   labels={'Vous habitez dans :': 'Type de logement', 'De quel type d\'accident s\'agissait-il ?': 'Type d\'accident'})
        st.plotly_chart(fig_housing)

        # Analyse des habitudes de consommation de tabac et risque d'accidents
        fig_tabac = px.histogram(dfs['individu'], x="Combien fumez-vous ou fumiez-vous de cigarettes, cigarillos, cigares ou pipes par jour ?", 
                                 color="Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?", 
                                 title="Relation entre la consommation de tabac et les accidents",
                                 labels={'Combien fumez-vous ou fumiez-vous de cigarettes, cigarillos, cigares ou pipes par jour ?': 'Consommation de tabac (par jour)', 
                                         'Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?': 'Accidents'})
        st.plotly_chart(fig_tabac)

        # Analyse de l'influence de la consommation de cannabis sur les accidents
        fig_cannabis = px.histogram(dfs['individu'], x="Avez-vous consommé du cannabis (haschisch, marijuana, herbe, joint, shit) au cours des 30 derniers jours ?", 
                                    color="Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?", 
                                    title="Relation entre la consommation de cannabis et les accidents",
                                    labels={'Avez-vous consommé du cannabis (haschisch, marijuana, herbe, joint, shit) au cours des 30 derniers jours ?': 'Consommation de cannabis', 
                                            'Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?': 'Accidents'})
        st.plotly_chart(fig_cannabis)

        # Analyse des conditions physiques et mentales par rapport aux accidents
        fig_physical_mental = px.scatter(dfs['individu'], x="Sur cette échelle de 1 à 10, en moyenne au cours de la semaine passée, comment vous êtes-vous senti sur le plan physique ?", 
                                         y="Sur cette échelle de 1 à 10, en moyenne au cours de la semaine passée, comment vous êtes-vous senti sur le plan mental ?", 
                                         color="Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?", 
                                         title="Influence des conditions physiques et mentales sur les accidents",
                                         labels={'Sur cette échelle de 1 à 10, en moyenne au cours de la semaine passée, comment vous êtes-vous senti sur le plan physique ?': 'État physique', 
                                                 'Sur cette échelle de 1 à 10, en moyenne au cours de la semaine passée, comment vous êtes-vous senti sur le plan mental ?': 'État mental',
                                                 'Au cours des 12 derniers mois, avez-vous eu un ou des accidents ?': 'Accidents'})
        st.plotly_chart(fig_physical_mental)

else:
    st.warning("Veuillez télécharger tous les fichiers nécessaires pour commencer l'analyse.")

