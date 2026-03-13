#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单演示服务器，用于快速演示功能
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 模拟数据
dishes = [
    {"id": 1, "name": "香煎鸡腿饭", "price": 28, "category_id": 1, "description": "外酥里嫩的鸡腿肉，搭配秘制酱汁", "image": "/static/dish/chicken.jpg", "sales": 120, "rating": 4.8},
    {"id": 2, "name": "黑椒牛肉饭", "price": 32, "category_id": 1, "description": "精选澳洲牛肉，搭配黑胡椒酱汁", "image": "/static/dish/beef.jpg", "sales": 98, "rating": 4.7},
    {"id": 3, "name": "鳕鱼饭", "price": 36, "category_id": 1, "description": "深海鳕鱼，营养丰富", "image": "/static/dish/fishrice.png", "sales": 75, "rating": 4.9},
    {"id": 4, "name": "红烧肉饭", "price": 26, "category_id": 1, "description": "肥而不腻，入口即化", "image": "/static/dish/pork.jpg", "sales": 150, "rating": 4.6},
    {"id": 5, "name": "可乐", "price": 5, "category_id": 2, "description": "冰镇可口可乐", "image": "/static/dish/cola.jpg", "sales": 200, "rating": 4.5},
    {"id": 6, "name": "紫菜蛋花汤", "price": 8, "category_id": 3, "description": "鲜美的紫菜蛋花汤", "image": "/static/dish/soup.jpg", "sales": 85, "rating": 4.4},
]

categories = [
    {"id": 1, "name": "主食", "icon": "🍚"},
    {"id": 2, "name": "饮料", "icon": "🥤"},
    {"id": 3, "name": "汤品", "icon": "🍲"},
    {"id": 4, "name": "小吃", "icon": "🍟"},
]

orders = []
users = []

# 健康检查
@app.route('/api/v1/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "HotMeal API is running", "timestamp": datetime.now().isoformat()})

# 获取菜品列表
@app.route('/api/v1/dishes', methods=['GET'])
def get_dishes():
    category_id = request.args.get('category_id', type=int)
    if category_id:
        filtered_dishes = [d for d in dishes if d['category_id'] == category_id]
        return jsonify(filtered_dishes)
    return jsonify(dishes)

# 获取分类列表
@app.route('/api/v1/categories', methods=['GET'])
def get_categories():
    return jsonify(categories)

# 获取推荐菜品
@app.route('/api/v1/recommend', methods=['GET'])
def get_recommend():
    # 简单返回销量最高的4个菜品
    sorted_dishes = sorted(dishes, key=lambda x: x['sales'], reverse=True)[:4]
    return jsonify(sorted_dishes)

# 用户登录
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # 简单演示，任何用户都可以登录
    return jsonify({
        "token": "demo-token-123456",
        "user": {
            "id": 1,
            "username": username,
            "nickname": "演示用户",
            "avatar": "/static/default-avatar.png",
            "phone": "13800138000"
        }
    })

# 用户注册
@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    return jsonify({
        "message": "注册成功",
        "user": {
            "id": len(users) + 1,
            "username": data.get('username'),
            "nickname": data.get('nickname', '新用户'),
            "avatar": "/static/default-avatar.png"
        }
    })

# 创建订单
@app.route('/api/v1/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    order_id = len(orders) + 1
    order = {
        "id": order_id,
        "order_no": f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{order_id:04d}",
        "user_id": 1,
        "total_amount": data.get('total_amount', 0),
        "status": "pending",
        "items": data.get('items', []),
        "created_at": datetime.now().isoformat(),
        "pay_time": None
    }
    orders.append(order)
    return jsonify(order)

# 获取用户订单
@app.route('/api/v1/orders', methods=['GET'])
def get_orders():
    user_id = request.args.get('user_id', 1, type=int)
    status = request.args.get('status')
    
    user_orders = [o for o in orders if o['user_id'] == user_id]
    if status:
        user_orders = [o for o in user_orders if o['status'] == status]
    
    return jsonify(sorted(user_orders, key=lambda x: x['created_at'], reverse=True))

# 订单支付
@app.route('/api/v1/orders/<int:order_id>/pay', methods=['POST'])
def pay_order(order_id):
    for order in orders:
        if order['id'] == order_id:
            order['status'] = 'paid'
            order['pay_time'] = datetime.now().isoformat()
            return jsonify({"message": "支付成功", "order": order})
    return jsonify({"message": "订单不存在"}), 404

# 获取用户信息
@app.route('/api/v1/users/profile', methods=['GET'])
def get_profile():
    return jsonify({
        "id": 1,
        "username": "demo",
        "nickname": "演示用户",
        "avatar": "/static/default-avatar.png",
        "phone": "13800138000",
        "email": "demo@example.com",
        "created_at": "2025-01-01T00:00:00"
    })

# 更新用户信息
@app.route('/api/v1/users/profile', methods=['PUT'])
def update_profile():
    data = request.get_json()
    return jsonify({
        "message": "更新成功",
        "user": {
            "id": 1,
            "username": "demo",
            "nickname": data.get('nickname', '演示用户'),
            "avatar": data.get('avatar', '/static/default-avatar.png'),
            "phone": data.get('phone', '13800138000')
        }
    })

if __name__ == '__main__':
    print("🚀 HotMeal 演示服务器启动中...")
    print("📱 后端 API 地址: http://127.0.0.1:5001/api/v1")
    print("💡 这是演示版本，使用内存数据库，重启后数据会重置")
    app.run(host='0.0.0.0', port=5001, debug=True)
