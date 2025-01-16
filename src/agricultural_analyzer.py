import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.seasonal import seasonal_decompose

class AgriculturalAnalyzer:
    def __init__(self, data_manager):
        """
        Initialise l'analyseur avec le gestionnaire de données
        """
        self.data_manager = data_manager
        self.model = RandomForestRegressor(
            n_estimators=100,
            random_state=42
        )
        self.scaler = StandardScaler()
        
    def analyze_yield_factors(self, parcelle_id):
        """
        Analyse complète des facteurs influençant les rendements
        """
        # Récupérer les données historiques
        history = self.data_manager.yield_history[
            self.data_manager.yield_history['parcelle_id'] == parcelle_id
        ].copy()
        
        # Fusionner avec les données météo et sol
        merged_data = self._merge_historical_data(parcelle_id)
        
        # Calculer les corrélations
        correlations = self._calculate_yield_correlations(merged_data)
        
        # Identifier les facteurs limitants
        limiting_factors = self._identify_limiting_factors(merged_data, correlations)
        
        # Analyser la stabilité
        stability_metrics = self._analyze_yield_stability(history['rendement_estime'])
        
        # Détecter les points de rupture
        breakpoints = self._detect_yield_breakpoints(history['rendement_estime'])
        
        return {
            'correlations': correlations,
            'limiting_factors': limiting_factors,
            'stability': stability_metrics,
            'breakpoints': breakpoints
        }
    
    def _merge_historical_data(self, parcelle_id):
        """Fusionne les données historiques avec météo et sol"""
        history = self.data_manager.yield_history[
            self.data_manager.yield_history['parcelle_id'] == parcelle_id
        ].copy()
        
        # Fusionner avec les données météo
        weather = self.data_manager.weather_data.copy()
        weather['month'] = weather['date'].dt.month
        weather_agg = weather.groupby('month').agg({
            'temperature': 'mean',
            'humidite': 'mean'
        }).reset_index()
        
        history['month'] = history['date'].dt.month
        merged = pd.merge(history, weather_agg, on='month')
        
        # Ajouter les données de sol
        soil_data = self.data_manager.soil_data[
            self.data_manager.soil_data['parcelle_id'] == parcelle_id
        ]
        merged = pd.merge(merged, soil_data, on='parcelle_id')
        
        return merged

    def _calculate_yield_correlations(self, data):
        """Calcule les corrélations entre rendement et facteurs"""
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        correlations = {}
        
        for col in numeric_cols:
            if col != 'rendement_estime' and not col.startswith('month'):
                # Drop rows where either column contains NaN
                valid_data = data[[col, 'rendement_estime']].dropna()
                
                # Only calculate correlation if we have enough valid data points
                if len(valid_data) >= 2:  # Pearson correlation needs at least 2 points
                    try:
                        correlation = stats.pearsonr(valid_data['rendement_estime'], valid_data[col])
                        correlations[col] = {
                            'coefficient': correlation[0],
                            'p_value': correlation[1]
                        }
                    except Exception as e:
                        # Handle any remaining numerical issues
                        correlations[col] = {
                            'coefficient': 0,
                            'p_value': 1,
                            'error': str(e)
                        }
                else:
                    correlations[col] = {
                        'coefficient': 0,
                        'p_value': 1,
                        'error': 'insufficient_data'
                    }
        
        return correlations

    def _identify_limiting_factors(self, data, correlations):
        """
        Identifie les facteurs limitants selon la loi de Liebig
        """
        limiting_factors = []
        
        # Définir les seuils optimaux pour chaque facteur
        optimal_thresholds = {
            'temperature': {'min': 15, 'max': 25},
            'humidite': {'min': 60, 'max': 80}
        }
        
        for factor, threshold in optimal_thresholds.items():
            if factor in data.columns:
                current_value = data[factor].mean()
                correlation = correlations.get(factor, {'coefficient': 0})['coefficient']
                
                if current_value < threshold['min']:
                    limiting_factors.append({
                        'factor': factor,
                        'status': 'low',
                        'current': current_value,
                        'optimal_min': threshold['min'],
                        'correlation': correlation,
                        'impact': 'negative' if correlation > 0 else 'positive'
                    })
                elif current_value > threshold['max']:
                    limiting_factors.append({
                        'factor': factor,
                        'status': 'high',
                        'current': current_value,
                        'optimal_max': threshold['max'],
                        'correlation': correlation,
                        'impact': 'negative' if correlation > 0 else 'positive'
                    })
        
        return limiting_factors

    def _analyze_yield_stability(self, yield_series):
        """
        Analyse la stabilité des rendements
        """
        # Décomposition de la série temporelle
        decomposition = seasonal_decompose(yield_series, period=12, extrapolate_trend='freq')
        
        stability_metrics = {
            'mean': yield_series.mean(),
            'cv': (yield_series.std() / yield_series.mean()) * 100,  # Coefficient de variation
            'trend_slope': stats.linregress(np.arange(len(yield_series)), yield_series)[0],
            'volatility': yield_series.std(),
            'stability_index': self._calculate_stability_index(yield_series)
        }
        
        return stability_metrics

    def _calculate_stability_index(self, yield_series):
        """
        Calcule un index de stabilité personnalisé
        Combine la variabilité et la tendance
        """
        # Normaliser la série
        normalized = (yield_series - yield_series.mean()) / yield_series.std()
        
        # Calculer la tendance
        trend = stats.linregress(np.arange(len(normalized)), normalized)
        
        # Calculer la variabilité relative
        cv = (yield_series.std() / yield_series.mean()) * 100
        
        # Combiner tendance et variabilité dans un index
        # Un index plus élevé indique une meilleure stabilité
        stability_index = (1 / (1 + cv)) * (1 + max(0, trend.slope))
        
        return stability_index

    def _detect_yield_breakpoints(self, yield_series):
        """
        Détecte les changements significatifs dans la série
        """
        # Calculer les différences relatives
        rel_changes = yield_series.pct_change()
        
        # Définir un seuil pour les changements significatifs
        threshold = 2 * rel_changes.std()
        
        # Identifier les points de rupture
        breakpoints = []
        for date, change in zip(yield_series.index[1:], rel_changes[1:]):
            if abs(change) > threshold:
                breakpoints.append({
                    'date': date,
                    'change': change,
                    'value': yield_series[date],
                    'type': 'increase' if change > 0 else 'decrease'
                })
        
        return breakpoints