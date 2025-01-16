import pandas as pd
import streamlit as st
import folium
import plotly.express as px
from streamlit_folium import folium_static
import warnings
warnings.filterwarnings('ignore')

from agricultural_analyzer import AgriculturalAnalyzer
from data_manager import AgriculturalDataManager
from report_generator import AgriculturalReportGenerator

class EnhancedAgriculturalDashboard:
    def __init__(self):
        self.data_manager = AgriculturalDataManager()
        self.analyzer = AgriculturalAnalyzer(self.data_manager)
        self.report_generator = AgriculturalReportGenerator(self.analyzer, self.data_manager)


    def run(self):
        """Lance le tableau de bord"""
        st.title('Tableau de Bord Agricole Amélioré')
        
        # Chargement des données
        self.data_manager.load_data()
        
        # Sélecteur de parcelle
        parcelles = sorted(self.data_manager.monitoring_data['parcelle_id'].unique())
        selected_parcelle = st.selectbox('Sélectionner une parcelle:', parcelles)
        
        # Affichage du dashboard
        self.create_dashboard(selected_parcelle)
    
    def create_dashboard(self, selected_parcelle):
        """Crée le tableau de bord pour une parcelle sélectionnée"""
        # Filtrer les données pour la parcelle sélectionnée
        parcel_monitoring = self.data_manager.monitoring_data[
            self.data_manager.monitoring_data['parcelle_id'] == selected_parcelle
        ]
        
        # Afficher les métriques clés
        self.display_key_metrics(selected_parcelle, parcel_monitoring)
        
        # Créer les visualisations
        col1, col2 = st.columns(2)
        
        with col1:
            self.plot_ndvi_evolution(parcel_monitoring)
            self.plot_stress_evolution(parcel_monitoring)
        
        with col2:
            self.plot_yield_history(selected_parcelle)
            self.plot_weather_correlation(selected_parcelle)
        
        # Afficher la carte
        self.display_map(selected_parcelle)
    
        if st.button("Générer un rapport"):
            with st.spinner("Génération du rapport en cours..."):
                pdf_path = self.report_generator.generate_parcelle_report(selected_parcelle)
                st.success(f"Rapport généré : {pdf_path}")


    def display_key_metrics(self, parcelle_id, parcel_data):
        """Affiche les métriques clés avec des indicateurs de risque"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            latest_ndvi = parcel_data['ndvi'].iloc[-1] if not parcel_data.empty else 0
            st.metric("NDVI actuel", f"{latest_ndvi:.2f}")
        
        with col2:
            avg_yield = self.data_manager.yield_history[
                self.data_manager.yield_history['parcelle_id'] == parcelle_id
            ]['rendement_estime'].mean() if not parcel_data.empty else 0
            st.metric("Rendement moyen", f"{avg_yield:.1f} t/ha")
        
        with col3:
            latest_stress = parcel_data['stress_hydrique'].iloc[-1] if not parcel_data.empty else 0
            st.metric("Stress hydrique", f"{latest_stress:.1f}%")
        
        with col4:
            risk_score = self.data_manager.calculate_risk_metrics(parcelle_id)
            emoji = "🔴" if risk_score > 0.7 else "🟠" if risk_score > 0.4 else "🟢"
            st.metric("Score de risque", f"{emoji} {risk_score:.2f}")

    
    def plot_ndvi_evolution(self, parcel_data):
        """Trace l'évolution du NDVI avec la moyenne mobile"""
        if not parcel_data.empty:
            parcel_data['ndvi_ma'] = parcel_data['ndvi'].rolling(window=7).mean()
            
            fig = px.line(parcel_data, 
                         x='date', 
                         y=['ndvi', 'ndvi_ma'],
                         title='Évolution du NDVI',
                         labels={'value': 'NDVI', 'variable': 'Métrique'},
                         color_discrete_map={'ndvi': 'blue', 'ndvi_ma': 'red'})
            st.plotly_chart(fig)
    
    def plot_stress_evolution(self, parcel_data):
        """Trace l'évolution du stress hydrique"""
        if not parcel_data.empty:
            fig = px.line(parcel_data,
                         x='date',
                         y='stress_hydrique',
                         title='Évolution du Stress Hydrique')
            st.plotly_chart(fig)
    
    def plot_yield_history(self, parcelle_id):
        """Trace l'historique des rendements avec tendance"""
        parcel_yields = self.data_manager.yield_history[
            self.data_manager.yield_history['parcelle_id'] == parcelle_id
        ]
        
        if not parcel_yields.empty:
            fig = px.bar(parcel_yields,
                        x='date',
                        y='rendement_estime',
                        title='Historique des Rendements')
            st.plotly_chart(fig)
    
    def plot_weather_correlation(self, parcelle_id):
        """Trace la corrélation entre la météo et le NDVI"""
        merged_data = pd.merge(
            self.data_manager.monitoring_data[self.data_manager.monitoring_data['parcelle_id'] == parcelle_id],
            self.data_manager.weather_data,
            on='date',
            how='inner'
        )
        
        if not merged_data.empty:
            fig = px.scatter(merged_data,
                           x='temperature',
                           y='ndvi',
                           title='Corrélation Température-NDVI',
                           trendline="ols")
            st.plotly_chart(fig)
    
    def display_map(self, selected_parcelle):
        """Affiche la carte des parcelles avec indicateurs de risque"""
        try:
            parcels_data = self.data_manager.monitoring_data.dropna(subset=['latitude', 'longitude'])
            
            if parcels_data.empty:
                st.error("Pas de données géographiques disponibles")
                return
                
            # Centrer la carte sur la parcelle sélectionnée
            selected_parcel_data = parcels_data[parcels_data['parcelle_id'] == selected_parcelle]
            center_lat = selected_parcel_data['latitude'].iloc[0]
            center_lon = selected_parcel_data['longitude'].iloc[0]
            
            m = folium.Map(location=[center_lat, center_lon], 
                          zoom_start=12)
            
            # Ajouter les marqueurs pour chaque parcelle
            for _, row in parcels_data.drop_duplicates('parcelle_id').iterrows():
                risk_score = self.data_manager.calculate_risk_metrics(row['parcelle_id'])
                color = 'red' if risk_score > 0.7 else 'orange' if risk_score > 0.4 else 'green'
                
                popup_text = f"""
                    <b>Parcelle:</b> {row['parcelle_id']}<br>
                    <b>Score de risque:</b> {risk_score:.2f}<br>
                    <b>NDVI actuel:</b> {row['ndvi']:.2f}
                """
                
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=10,
                    popup=popup_text,
                    color=color,
                    fill=True,
                    fill_opacity=0.7
                ).add_to(m)
            
            st.subheader('Carte des Parcelles')
            folium_static(m)

        except Exception as e:
            st.error(f"Erreur lors de l'affichage de la carte : {str(e)}")

        st.subheader("Analyse Détaillée")
        
        # Obtenir l'analyse complète
        analysis = self.analyzer.analyze_yield_factors(selected_parcelle)
        
        # Afficher les facteurs limitants
        st.write("### Facteurs Limitants")
        for factor in analysis['limiting_factors']:
            st.warning(
                f"**{factor['factor']}**: {factor['status'].title()} "
                f"(Actuel: {factor['current']:.1f}, "
                f"Impact: {factor['impact']})"
            )
        
        # Afficher les corrélations importantes
        st.write("### Corrélations Principales")
        corr_df = pd.DataFrame([
            {
                'Facteur': k,
                'Coefficient': v['coefficient'],
                'P-value': v['p_value']
            }
            for k, v in analysis['correlations'].items()
        ])
        st.dataframe(corr_df)
        
        # Afficher les métriques de stabilité
        st.write("### Métriques de Stabilité")
        stability = analysis['stability']
        col1, col2, col3 = st.columns(3)
        col1.metric("Coefficient de Variation", f"{stability['cv']:.1f}%")
        col2.metric("Tendance", f"{stability['trend_slope']:.3f}")
        col3.metric("Index de Stabilité", f"{stability['stability_index']:.2f}")

def main():
    dashboard = EnhancedAgriculturalDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()