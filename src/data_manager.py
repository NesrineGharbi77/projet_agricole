import pandas as pd
import numpy as np
import streamlit as st
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')




class AgriculturalDataManager:
    def __init__(self):
        self.monitoring_data = None
        self.weather_data = None
        self.soil_data = None
        self.yield_history = None
        self.scaler = StandardScaler()
    
    def load_data(self):
        """Charge les données depuis les fichiers CSV avec vérification"""
        try:
            self.monitoring_data = pd.read_csv(r'C:\Users\Nesrine\Downloads\monitoring_cultures.csv', parse_dates=['date'])
            self.weather_data = pd.read_csv(r'C:\Users\Nesrine\Downloads\meteo_detaillee.csv', parse_dates=['date'])
            self.soil_data = pd.read_csv(r'C:\Users\Nesrine\Downloads\sols.csv')
            self.yield_history = pd.read_csv(r'C:\Users\Nesrine\Downloads\historique_rendements.csv', parse_dates=['date'])
            
            self._verify_data_integrity()
        except Exception as e:
            st.error(f"Erreur lors du chargement des données: {str(e)}")
    
    def _verify_data_integrity(self):
        """Vérifie l'intégrité des données chargées"""
        required_columns = {
            'monitoring_data': ['parcelle_id', 'date', 'ndvi', 'stress_hydrique', 'latitude', 'longitude'],
            'weather_data': ['date', 'temperature', 'humidite'],
            'soil_data': ['parcelle_id', 'type_sol'],
            'yield_history': ['parcelle_id', 'date', 'rendement_estime']
        }
        
        for dataset_name, columns in required_columns.items():
            dataset = getattr(self, dataset_name)
            missing_columns = [col for col in columns if col not in dataset.columns]
            if missing_columns:
                raise ValueError(f"Colonnes manquantes dans {dataset_name}: {missing_columns}")
    
    def calculate_risk_metrics(self, parcelle_id):
        """Calcule les métriques de risque pour une parcelle"""
        parcel_data = self.monitoring_data[self.monitoring_data['parcelle_id'] == parcelle_id].copy()
        
        if not parcel_data.empty:
            # Calcul du risque de stress hydrique
            parcel_data['risk_score'] = (
                parcel_data['stress_hydrique'] / 100 * 0.7 +
                (1 - parcel_data['ndvi']) * 0.3
            )
            
            return parcel_data['risk_score'].iloc[-1]
        return 0