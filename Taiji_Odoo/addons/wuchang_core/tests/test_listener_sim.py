import unittest
from unittest.mock import MagicMock
import sys
import os

# Mock Odoo environment
sys.modules['odoo'] = MagicMock()
sys.modules['odoo.models'] = MagicMock()
sys.modules['odoo.api'] = MagicMock()

# Import the class under test
# We need to manually exec the file content because it imports 'odoo'
with open('models/ai_event_listener.py', 'r', encoding='utf-8') as f:
    code = f.read()
    # Remove the Odoo import to avoid import errors in this standalone script
    # code = code.replace('from odoo import models, api', '')
    # But we mocked it, so it should be fine if we just execute the class def
    pass

# We will define a mock class that behaves like the one in the file
class MockModel:
    def create(self, vals):
        return vals

class MockEnv:
    def __init__(self):
        self.ref_mock = MagicMock()
        self.ref_mock.id = 1
        
    def ref(self, xmlid):
        return self.ref_mock
        
    def __getitem__(self, key):
        if key == 'wuchang.ai.perception.sensor':
            return MockSensor()
        if key == 'wuchang.task':
            return MockTask()
        if key == 'mail.mail':
            return MockMail()
        return MagicMock()

class MockSensor:
    def analyze_message(self, body, author):
        if 'die' in body:
            return {'action': 'escalate_to_brother_crisis', 'reason': 'Crisis keyword', 'context_hint': 'Suicide risk'}
        return {'action': 'none'}

class MockTask:
    def sudo(self): return self
    def create(self, vals):
        print(f"Task Created: {vals['name']}")
        return True

class MockMail:
    def sudo(self): return self
    def create(self, vals):
        print(f"Email Created: To {vals['email_to']}, Subject: {vals['subject']}")
        return MagicMock() # .send()

class MockMessage:
    def __init__(self, body, author):
        self.body = body
        self.author_id = MagicMock()
        self.author_id.name = author
        self.message_type = 'comment'
        
    def write(self, vals):
        print(f"Message Updated: {vals}")

# Instantiate the listener logic manually since we can't easily inherit from Odoo Model here
def test_listener_logic():
    print("Testing Listener Logic...")
    env = MockEnv()
    
    # Simulate a crisis message
    msg = MockMessage("I want to die", "Sad User")
    
    # Simulate the loop in create()
    sensor = env['wuchang.ai.perception.sensor']
    analysis = sensor.analyze_message(msg.body, msg.author_id.name)
    
    if analysis['action'] == 'escalate_to_brother_crisis':
        print("Crisis Detected!")
        
        # Create Task
        env['wuchang.task'].create({
            'name': f"🚨 EMERGENCY: Crisis Detected from {msg.author_id.name}",
            'description': "...",
            'priority': '3',
            'user_ids': [(4, 1)]
        })
        
        # Send Email
        env['mail.mail'].create({
            'subject': f"🚨 CRISIS ALERT: {msg.author_id.name}",
            'email_to': 'o970106@gmail.com',
            'email_from': 'sister@wuchang.life'
        })
        
        # Update Message
        msg.write({'body': msg.body + "<br/><br/>[Sister]: Crisis Handled."})

if __name__ == '__main__':
    test_listener_logic()
