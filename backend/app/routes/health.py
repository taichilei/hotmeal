"""
@File       : health.py
@Date       : 2025-03-01
@Desc       : Health check related APIs
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
