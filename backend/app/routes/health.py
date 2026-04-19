"""
@File       : health.py
@Author     : ChiLei Tai JOU
@Date       : 2025-03-01
@Description: 健康检查相关 API
"""

from flask_restx import Namespace, Resource

api = Namespace('health', description='Health check related APIs')


@api.route('')
class Health(Resource):
    @api.doc('Health check')
    def get(self):
        """Health check endpoint"""
        return {
            'status': 'ok',
            'message': 'Service is running'
        }
