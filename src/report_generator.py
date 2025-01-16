import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
import subprocess
import matplotlib.pyplot as plt
import seaborn as sns
import os
import subprocess
import shutil



class AgriculturalReportGenerator:
    def __init__(self, analyzer, data_manager):
        self.analyzer = analyzer
        self.data_manager = data_manager
        self.report_path = r"C:\Users\Nesrine\Desktop\projet_agricole\reports"
        os.makedirs(self.report_path, exist_ok=True)  # Crée le répertoire s'il n'existe pas
    
    def generate_parcelle_report(self, parcelle_id):
        """Génère un rapport complet pour une parcelle"""
        # Récupérer les analyses
        analysis = self.analyzer.analyze_yield_factors(parcelle_id)
        current_state = self._get_current_state(parcelle_id)
        
        # Générer les figures
        figures = self._generate_report_figures(parcelle_id, analysis)
        
        # Créer le contenu markdown
        markdown_content = self._create_markdown_report(
            parcelle_id, analysis, current_state, figures
        )
        
        # Convertir en PDF
        pdf_path = self._convert_to_pdf(markdown_content, parcelle_id)
        
        return pdf_path
    
    def _get_current_state(self, parcelle_id):
        """Récupère l'état actuel de la parcelle"""
        current_data = self.data_manager.monitoring_data[
            self.data_manager.monitoring_data['parcelle_id'] == parcelle_id
        ].iloc[-1]
        
        return {
            'ndvi': current_data['ndvi'],
            'stress_hydrique': current_data['stress_hydrique'],
            'date': current_data['date']
        }
    
    def _create_markdown_report(self, parcelle_id, analysis, current_state, figures):
        """Crée le contenu du rapport en markdown"""
        report_date = datetime.now().strftime("%d/%m/%Y")
        
        markdown = f"""
        # Rapport d'Analyse Agricole - Parcelle {parcelle_id}
        *Généré le {report_date}*

        ## État Actuel
        - **NDVI**: {current_state['ndvi']:.2f}
        - **Stress Hydrique**: {current_state['stress_hydrique']:.1f}%
        - **Date des mesures**: {current_state['date']}

        ## Analyse des Rendements

        ### Facteurs Limitants
        """
        
        # Ajouter les facteurs limitants
        for factor in analysis['limiting_factors']:
            markdown += f"- **{factor['factor']}**: {factor['status'].title()}\n"
            markdown += f"  - Valeur actuelle: {factor['current']:.1f}\n"
            markdown += f"  - Impact: {factor['impact']}\n\n"
        
        # Ajouter les métriques de stabilité
        stability = analysis['stability']
        markdown += """
### Stabilité des Rendements
"""
        markdown += f"- Coefficient de variation: {stability['cv']:.1f}%\n"
        markdown += f"- Tendance: {stability['trend_slope']:.3f}\n"
        markdown += f"- Index de stabilité: {stability['stability_index']:.2f}\n"
        
        # Ajouter les points de rupture
        markdown += "\n### Points de Rupture Significatifs\n"
        for point in analysis['breakpoints']:
            markdown += f"- **{point['date']}**: "
            markdown += f"{point['type'].title()} de {abs(point['change']*100):.1f}%\n"
        
        # Ajouter les recommandations
        markdown += "\n## Recommandations\n"
        recommendations = self._generate_recommendations(analysis, current_state)
        for rec in recommendations:
            markdown += f"- {rec}\n"
        
        return markdown
    
    def _generate_report_figures(self, parcelle_id, analysis):
        """Génère les figures pour le rapport"""
        figures = {}
        
        # Figure 1: Évolution des rendements
        plt.figure(figsize=(10, 6))
        history = self.data_manager.yield_history[
            self.data_manager.yield_history['parcelle_id'] == parcelle_id
        ]
        plt.plot(history['date'], history['rendement_estime'])
        plt.title('Évolution des Rendements')
        plt.xlabel('Date')
        plt.ylabel('Rendement (t/ha)')
        figures['yield_evolution'] = f"{self.report_path}/yield_evolution_{parcelle_id}.png"
        plt.savefig(figures['yield_evolution'])
        plt.close()
        
        # Figure 2: Matrice de corrélation
        plt.figure(figsize=(8, 8))
        data = self._merge_historical_data(parcelle_id)
        sns.heatmap(data.corr(), annot=True, cmap='coolwarm')
        plt.title('Matrice de Corrélation')
        figures['correlation_matrix'] = f"{self.report_path}/correlation_matrix_{parcelle_id}.png"
        plt.savefig(figures['correlation_matrix'])
        plt.close()
        
        return figures
    
    def _merge_historical_data(self, parcelle_id):
        history = self.data_manager.yield_history[
            self.data_manager.yield_history['parcelle_id'] == parcelle_id
        ].copy()
        
        weather = self.data_manager.weather_data.copy()
        weather['month'] = weather['date'].dt.month
        weather_agg = weather.groupby('month').agg({
            'temperature': 'mean',
            'humidite': 'mean'
        }).reset_index()
        
        history['month'] = history['date'].dt.month
        merged = pd.merge(history, weather_agg, on='month')
        
        # Garder uniquement les colonnes numériques
        numeric_data = merged.select_dtypes(include=['float64', 'int64'])
    
        return numeric_data

    
    def _generate_recommendations(self, analysis, current_state):
        """Génère des recommandations basées sur l'analyse"""
        recommendations = []
        
        # Recommandations basées sur les facteurs limitants
        for factor in analysis['limiting_factors']:
            if factor['status'] == 'low':
                recommendations.append(
                    f"Augmenter le niveau de {factor['factor']} pour optimiser les rendements"
                )
            else:
                recommendations.append(
                    f"Réduire le niveau de {factor['factor']} pour éviter les impacts négatifs"
                )
        
        # Recommandations basées sur la stabilité
        stability = analysis['stability']
        if stability['cv'] > 20:
            recommendations.append(
                "Mettre en place des mesures pour réduire la variabilité des rendements"
            )
        
        # Recommandations basées sur l'état actuel
        if current_state['stress_hydrique'] > 50:
            recommendations.append(
                "Intervention urgente nécessaire pour réduire le stress hydrique"
            )
        if current_state['ndvi'] < 0.5:
            recommendations.append(
                "Surveiller l'état de la végétation et envisager une fertilisation"
            )
        
        return recommendations
    
    def _convert_to_pdf(self, markdown_content, parcelle_id):
        """Convertit le contenu Markdown en PDF."""
        # Définir les chemins des fichiers
        md_path = os.path.join(self.report_path, f"report_{parcelle_id}.md")
        pdf_path = os.path.join(self.report_path, f"report_{parcelle_id}.pdf")
        
        # Écrire le contenu Markdown dans un fichier temporaire
        try:
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        except Exception as e:
            print(f"Erreur lors de l'écriture du fichier Markdown : {str(e)}")
            return None

        # Vérifier si 'pandoc' est disponible
        if not shutil.which('pandoc'):
            print("Erreur : Pandoc n'est pas installé ou n'est pas dans le PATH.")
            return md_path  # Retourne le fichier Markdown si conversion impossible

        try:
            # Convertir en PDF avec pandoc
            subprocess.run([
                'pandoc',
                md_path,
                '-o', pdf_path,
                '--pdf-engine=xelatex',
                '-V', 'geometry:margin=1in'
            ], check=True)  # `check=True` lève une exception si la commande échoue
            
            # Vérifier que le PDF a été créé avec succès
            if os.path.exists(pdf_path):
                return pdf_path
            else:
                print("Erreur : Le fichier PDF n'a pas été généré.")
                return md_path
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de la conversion en PDF avec Pandoc : {str(e)}")
            return md_path
        except Exception as e:
            print(f"Erreur inconnue : {str(e)}")
            return md_path