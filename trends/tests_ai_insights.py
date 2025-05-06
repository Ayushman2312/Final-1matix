import json
import unittest
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from .views import AiInsightsApiView

class AiInsightsApiTests(TestCase):
    """
    Tests for the AI Insights API endpoint
    """
    
    def setUp(self):
        self.client = Client()
        self.ai_insights_url = reverse('trends:ai_insights_api')
        self.sample_trend_data = {
            "keyword": "test keyword",
            "timeframe": "last 5 years",
            "region": "India",
            "trendStats": {
                "peakInterest": {
                    "value": 100,
                    "date": "2023-01-15"
                },
                "lowestInterest": {
                    "value": 25,
                    "date": "2020-06-01"
                },
                "overallTrend": {
                    "direction": "increasing",
                    "percentage": "45.5"
                },
                "seasonality": {
                    "highestMonth": "December",
                    "lowestMonth": "June"
                },
                "recentTrend": "strong upward"
            },
            "dataPoints": [
                {"date": "2020-01-01", "value": 50},
                {"date": "2020-06-01", "value": 25},
                {"date": "2021-01-01", "value": 60},
                {"date": "2021-06-01", "value": 35},
                {"date": "2022-01-01", "value": 70},
                {"date": "2022-06-01", "value": 45},
                {"date": "2023-01-15", "value": 100}
            ]
        }
        
    @patch('trends.views.check_api_configuration')
    def test_missing_keyword(self, mock_check_api):
        """Test API response when keyword is missing"""
        mock_check_api.return_value = {'google_api_configured': True}
        
        response = self.client.post(
            self.ai_insights_url,
            json.dumps({"trend_data": self.sample_trend_data}),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['error'], 'Missing keyword parameter')
        
    @patch('trends.views.check_api_configuration')
    def test_missing_trend_data(self, mock_check_api):
        """Test API response when trend data is missing"""
        mock_check_api.return_value = {'google_api_configured': True}
        
        response = self.client.post(
            self.ai_insights_url,
            json.dumps({"keyword": "test"}),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['error'], 'Missing trend data')
        
    @patch('trends.views.check_api_configuration')
    def test_google_api_not_configured(self, mock_check_api):
        """Test API response when Google API is not configured"""
        mock_check_api.return_value = {'google_api_configured': False}
        
        response = self.client.post(
            self.ai_insights_url,
            json.dumps({
                "keyword": "test keyword",
                "trend_data": self.sample_trend_data
            }),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['error'], 'Google API is not configured')
        self.assertIn('insights', data)
        self.assertIn('trend_analysis', data['insights'])
        
    @patch('trends.views.check_api_configuration')
    @patch('trends.views.AiInsightsApiView.generate_comprehensive_insights')
    def test_successful_insights_generation(self, mock_generate_insights, mock_check_api):
        """Test successful generation of AI insights"""
        mock_check_api.return_value = {'google_api_configured': True}
        mock_insights = {
            'trend_analysis': 'Test trend analysis',
            'future_scope': 'Test future scope',
            'ad_recommendations': 'Test ad recommendations',
            'keyword_tips': 'Test keyword tips'
        }
        mock_generate_insights.return_value = mock_insights
        
        response = self.client.post(
            self.ai_insights_url,
            json.dumps({
                "keyword": "test keyword",
                "trend_data": self.sample_trend_data
            }),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['insights'], mock_insights)
        
    @patch('trends.views.check_api_configuration')
    @patch('trends.views.get_google_api_key')
    def test_missing_api_key(self, mock_get_api_key, mock_check_api):
        """Test response when Google API key is missing"""
        mock_check_api.return_value = {'google_api_configured': True}
        mock_get_api_key.return_value = None
        
        response = self.client.post(
            self.ai_insights_url,
            json.dumps({
                "keyword": "test keyword",
                "trend_data": self.sample_trend_data
            }),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertIn('insights', data)
        self.assertIn('trend_analysis', data['insights'])
        self.assertIn('API key not found', data['insights']['trend_analysis']) 