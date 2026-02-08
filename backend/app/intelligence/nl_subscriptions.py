"""
Natural Language Subscription Manager

Parses natural language to:
- Create subscriptions: "Tell me top revenue weekly"
- Cancel subscriptions: "Unsubscribe from that" / "Stop the revenue alerts"
- List subscriptions: "What am I subscribed to?"

Integrates with ChatInterface for seamless UX.
"""

import re
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from app.intelligence.subscriptions import (
    SubscriptionService,
    SubscriptionFrequency,
    SubscriptionCondition,
    SubscriptionConditionType,
    QuerySubscription
)
from app.services.chat_sessions import get_chat_session_service


class NLSubscriptionParser:
    """Parse natural language into subscription actions"""
    
    # Frequency patterns
    FREQUENCY_PATTERNS = {
        SubscriptionFrequency.HOURLY: [
            r'\bevery hour\b', r'\bhourly\b', r'\beach hour\b',
            r'\bonce an hour\b', r'\bper hour\b'
        ],
        SubscriptionFrequency.DAILY: [
            r'\bevery day\b', r'\bdaily\b', r'\beach day\b',
            r'\bonce a day\b', r'\bper day\b'
        ],
        SubscriptionFrequency.WEEKLY: [
            r'\bevery week\b', r'\bweekly\b', r'\beach week\b',
            r'\bonce a week\b', r'\bper week\b'
        ],
        SubscriptionFrequency.MONTHLY: [
            r'\bevery month\b', r'\bmonthly\b', r'\beach month\b',
            r'\bonce a month\b', r'\bper month\b'
        ]
    }
    
    # Subscription trigger patterns
    SUBSCRIBE_PATTERNS = [
        r'\btell me\b',
        r'\bnotify me\b',
        r'\balert me\b',
        r'\blet me know\b',
        r'\bsend me\b',
        r'\bkeep me updated\b',
        r'\btrack\b',
        r'\bmonitor\b',
        r'\bwatch\b',
        r'\bsubscribe\b',
        r'\bset up\s+(?:an?\s+)?alert\b',
        r'\bcreate\s+(?:an?\s+)?subscription\b'
    ]
    
    # Unsubscribe trigger patterns
    UNSUBSCRIBE_PATTERNS = [
        r'\bunsubscribe\b',
        r'\bstop\s+(?:the\s+)?(?:alert|notification|update)s?\b',
        r'\bcancel\s+(?:the\s+)?(?:alert|notification|subscription)s?\b',
        r'\bturn off\s+(?:the\s+)?(?:alert|notification)s?\b',
        r'\bdisable\s+(?:the\s+)?(?:alert|notification)s?\b',
        r'\bend\s+(?:the\s+)?(?:alert|notification|subscription)s?\b',
        r'\bremove\s+(?:the\s+)?(?:alert|notification|subscription)s?\b',
        r"\bi don't want\s+(?:the\s+)?(?:alert|notification)s?\b",
        r'\bdelete\s+(?:the\s+)?(?:alert|notification|subscription)s?\b'
    ]
    
    # List subscriptions pattern
    LIST_PATTERNS = [
        r'\bwhat\s+(?:am|have)\s+i\s+subscribed\s+to\b',
        r'\bshow\s+(?:me\s+)?my\s+subscriptions\b',
        r'\blist\s+(?:my\s+)?(?:alert|notification|subscription)s?\b',
        r'\bwhat\s+(?:alert|notification|subscription)s?\s+do\s+i\s+have\b'
    ]
    
    # Condition patterns
    CONDITION_PATTERNS = {
        SubscriptionConditionType.THRESHOLD: [
            r'(?:above|over|more than|greater than)\s+(\d+(?:\.\d+)?)',
            r'(?:below|under|less than|fewer than)\s+(\d+(?:\.\d+)?)',
            r'(?:drops?|falls?)\s+(?:below|under|to)\s+(\d+(?:\.\d+)?)',
            r'(?:rises?|increases?|goes? up)\s+(?:above|over|to)\s+(\d+(?:\.\d+)?)',
            r'(?:at least|minimum)\s+(\d+(?:\.\d+)?)',
            r'(?:at most|maximum)\s+(\d+(?:\.\d+)?)'
        ],
        SubscriptionConditionType.NEW_ITEMS: [
            r'\bnew\s+(?:client|customer|order|sale|item|record)s?\b',
            r'\bwhen\s+(?:there\s+are\s+)?new\b',
            r'\bany\s+new\b'
        ],
        SubscriptionConditionType.CHANGE: [
            r'(?:change|chang|chang|drop|fall|rise|increase|decrease)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%',
            r'(?:more than|over|above)\s+(\d+(?:\.\d+)?)\s*%\s*(?:change|drop|fall|rise|increase)'
        ]
    }
    
    def parse_intent(self, text: str) -> Tuple[str, Optional[Dict]]:
        """
        Parse user intent from text
        Returns: (action, params)
        action: 'subscribe', 'unsubscribe', 'list', 'unknown'
        """
        text_lower = text.lower()
        
        # Check for unsubscribe intent
        for pattern in self.UNSUBSCRIBE_PATTERNS:
            if re.search(pattern, text_lower):
                # Try to extract what to unsubscribe from
                target = self._extract_unsubscribe_target(text_lower)
                return 'unsubscribe', {'target': target, 'original': text}
        
        # Check for list intent
        for pattern in self.LIST_PATTERNS:
            if re.search(pattern, text_lower):
                return 'list', {'original': text}
        
        # Check for subscribe intent
        for pattern in self.SUBSCRIBE_PATTERNS:
            if re.search(pattern, text_lower):
                params = self._extract_subscription_params(text_lower)
                params['original'] = text
                return 'subscribe', params
        
        return 'unknown', {'original': text}
    
    def _extract_subscription_params(self, text: str) -> Dict:
        """Extract subscription parameters from text"""
        params = {
            'query': None,
            'frequency': SubscriptionFrequency.WEEKLY,  # Default
            'condition_type': SubscriptionConditionType.ALWAYS,  # Default
            'condition_config': {},
            'name': None
        }
        
        # Extract frequency
        for freq, patterns in self.FREQUENCY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    params['frequency'] = freq
                    break
        
        # Extract condition
        for cond_type, patterns in self.CONDITION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    params['condition_type'] = cond_type
                    # Extract threshold value if present
                    if match.groups():
                        params['condition_config']['value'] = float(match.group(1))
                    break
        
        # Extract the query (remove subscription keywords)
        query = self._extract_query(text)
        params['query'] = query
        
        # Generate name from query
        params['name'] = self._generate_name(query, params['condition_type'])
        
        return params
    
    def _extract_query(self, text: str) -> str:
        """Extract the actual query from subscription text"""
        # Remove subscription trigger words
        query = text
        
        # Remove frequency phrases
        for freq_patterns in self.FREQUENCY_PATTERNS.values():
            for pattern in freq_patterns:
                query = re.sub(pattern, '', query, flags=re.IGNORECASE)
        
        # Remove subscribe trigger words
        for pattern in self.SUBSCRIBE_PATTERNS:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)
        
        # Clean up
        query = re.sub(r'\s+', ' ', query).strip()
        query = query.rstrip('.,;:!?')
        
        return query
    
    def _generate_name(self, query: str, condition_type: SubscriptionConditionType) -> str:
        """Generate a subscription name from query"""
        # Take first 5 words or so
        words = query.split()
        name = ' '.join(words[:5])
        
        # Add condition indicator
        if condition_type != SubscriptionConditionType.ALWAYS:
            name += f" ({condition_type.value})"
        
        return name[:50]  # Limit length
    
    def _extract_unsubscribe_target(self, text: str) -> Optional[str]:
        """Try to extract what user wants to unsubscribe from"""
        # Look for "the X alert" or "X subscription" patterns
        patterns = [
            r'(?:from|the)\s+(.+?)(?:\s+(?:alert|notification|subscription|update)s?|$)',
            r'stop\s+(?:the\s+)?(.+?)(?:\s+(?:alert|notification|subscription|update)s?|$)',
            r'cancel\s+(?:the\s+)?(.+?)(?:\s+(?:alert|notification|subscription|update)s?|$)',
            r'turn off\s+(?:the\s+)?(.+?)(?:\s+(?:alert|notification|subscription|update)s?|$)',
            r'that\s+(.+?)(?:\s+(?:alert|notification|subscription|update)s?|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                target = match.group(1).strip()
                # Clean up common words
                target = re.sub(r'\b(alert|notification|subscription|update)s?\b', '', target, flags=re.IGNORECASE)
                target = re.sub(r'\s+', ' ', target).strip()
                if target:
                    return target
        
        return None


class NLSubscriptionManager:
    """Manage subscriptions via natural language"""
    
    def __init__(self, subscription_service: SubscriptionService):
        self.parser = NLSubscriptionParser()
        self.service = subscription_service
    
    async def handle_message(
        self,
        text: str,
        user_id: str,
        tenant_id: str,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Handle a natural language subscription message
        Returns response dict with action taken
        """
        intent, params = self.parser.parse_intent(text)
        
        if intent == 'subscribe':
            return await self._handle_subscribe(params, user_id, tenant_id)
        
        elif intent == 'unsubscribe':
            return await self._handle_unsubscribe(params, user_id, tenant_id, session_id)
        
        elif intent == 'list':
            return await self._handle_list(user_id, tenant_id)
        
        else:
            return {
                'success': False,
                'action': 'unknown',
                'message': "I'm not sure if you want to subscribe, unsubscribe, or list subscriptions. Could you rephrase?",
                'suggestions': [
                    "Try: 'Alert me when revenue drops below $10k weekly'",
                    "Try: 'Stop the revenue alerts'",
                    "Try: 'What am I subscribed to?'"
                ]
            }
    
    async def _handle_subscribe(
        self,
        params: Dict,
        user_id: str,
        tenant_id: str
    ) -> Dict:
        """Handle subscription creation"""
        query = params.get('query')
        
        if not query or len(query) < 5:
            return {
                'success': False,
                'action': 'subscribe',
                'message': "I couldn't understand what you want to track. Could you be more specific?",
                'example': "Try: 'Tell me my top revenue clients weekly'"
            }
        
        try:
            # Create the subscription
            subscription = await self.service.create_subscription(
                user_id=user_id,
                tenant_id=tenant_id,
                name=params['name'],
                query_template=query,
                frequency=params['frequency'],
                condition=SubscriptionCondition(
                    type=params['condition_type'],
                    config=params['condition_config']
                ),
                description=f"Created from: {params['original']}"
            )
            
            # Format response
            freq_text = subscription.frequency
            condition_text = ""
            if subscription.condition_type != SubscriptionConditionType.ALWAYS.value:
                condition_text = f" when condition is met"
            
            return {
                'success': True,
                'action': 'subscribe',
                'subscription_id': subscription.id,
                'message': f"✅ I'll {subscription.name}{condition_text} {freq_text}.",
                'details': {
                    'name': subscription.name,
                    'frequency': subscription.frequency,
                    'condition': subscription.condition_type,
                    'next_run': subscription.next_run_at.isoformat() if subscription.next_run_at else None
                },
                'unsubscribe_hint': f"To stop this, just say 'unsubscribe from {subscription.name}' or 'stop that {subscription.frequency} alert'"
            }
            
        except Exception as e:
            return {
                'success': False,
                'action': 'subscribe',
                'message': f"I couldn't create that subscription: {str(e)}",
                'error': str(e)
            }
    
    async def _handle_unsubscribe(
        self,
        params: Dict,
        user_id: str,
        tenant_id: str,
        session_id: Optional[str] = None
    ) -> Dict:
        """Handle unsubscription"""
        target = params.get('target')
        
        # Get user's subscriptions
        subscriptions = await self.service.get_user_subscriptions(
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        if not subscriptions:
            return {
                'success': False,
                'action': 'unsubscribe',
                'message': "You don't have any active subscriptions to cancel."
            }
        
        # If no target specified, try to use recent subscription from session
        if not target and session_id:
            # Get recent subscriptions from session context
            target = await self._get_recent_subscription_target(session_id, user_id, tenant_id)
        
        if not target:
            # List subscriptions and ask user to specify
            sub_list = "\n".join([f"• {s.name} ({s.frequency})" for s in subscriptions[:5]])
            return {
                'success': False,
                'action': 'unsubscribe',
                'message': "Which subscription would you like to cancel?",
                'subscriptions': [
                    {'id': s.id, 'name': s.name, 'frequency': s.frequency}
                    for s in subscriptions
                ],
                'suggestion': f"Your subscriptions:\n{sub_list}\n\nSay 'unsubscribe from [name]' to cancel one."
            }
        
        # Find matching subscription
        matching = self._find_matching_subscription(subscriptions, target)
        
        if not matching:
            return {
                'success': False,
                'action': 'unsubscribe',
                'message': f"I couldn't find a subscription matching '{target}'.",
                'subscriptions': [
                    {'id': s.id, 'name': s.name, 'frequency': s.frequency}
                    for s in subscriptions
                ]
            }
        
        # Cancel the subscription
        try:
            success = await self.service.cancel_subscription(
                subscription_id=matching.id,
                user_id=user_id
            )
            
            if success:
                return {
                    'success': True,
                    'action': 'unsubscribe',
                    'subscription_id': matching.id,
                    'message': f"✅ I've cancelled '{matching.name}'. You won't receive {matching.frequency} updates anymore.",
                    'resubscribe_hint': f"To restart this later, just say: '{params['original'].replace('unsubscribe', 'tell me').replace('stop', 'tell me')}'"
                }
            else:
                return {
                    'success': False,
                    'action': 'unsubscribe',
                    'message': "I couldn't cancel that subscription. It may have already been removed."
                }
                
        except Exception as e:
            return {
                'success': False,
                'action': 'unsubscribe',
                'message': f"Error cancelling subscription: {str(e)}"
            }
    
    async def _handle_list(self, user_id: str, tenant_id: str) -> Dict:
        """Handle listing subscriptions"""
        subscriptions = await self.service.get_user_subscriptions(
            user_id=user_id,
            tenant_id=tenant_id,
            status='active'
        )
        
        if not subscriptions:
            return {
                'success': True,
                'action': 'list',
                'count': 0,
                'message': "You don't have any active subscriptions.",
                'hint': "Try saying: 'Alert me when revenue changes weekly'"
            }
        
        # Format subscription list
        items = []
        for sub in subscriptions:
            status = "🟢" if sub.status == 'active' else "⏸️"
            items.append(f"{status} {sub.name} ({sub.frequency})")
        
        return {
            'success': True,
            'action': 'list',
            'count': len(subscriptions),
            'message': f"You have {len(subscriptions)} active subscription(s):\n\n" + "\n".join(items),
            'subscriptions': [
                {
                    'id': s.id,
                    'name': s.name,
                    'frequency': s.frequency,
                    'status': s.status,
                    'next_run': s.next_run_at.isoformat() if s.next_run_at else None
                }
                for s in subscriptions
            ],
            'hint': "To cancel one, say 'unsubscribe from [name]' or just 'stop that' for the most recent."
        }
    
    def _find_matching_subscription(
        self,
        subscriptions: List[QuerySubscription],
        target: str
    ) -> Optional[QuerySubscription]:
        """Find subscription matching target text"""
        target_lower = target.lower()
        
        # Exact match first
        for sub in subscriptions:
            if sub.name.lower() == target_lower:
                return sub
        
        # Contains match
        for sub in subscriptions:
            if target_lower in sub.name.lower():
                return sub
        
        # Word match
        target_words = set(target_lower.split())
        for sub in subscriptions:
            sub_words = set(sub.name.lower().split())
            if target_words & sub_words:  # Any word matches
                return sub
        
        # Most recent if target is vague ("that", "it", "this")
        if target_lower in ['that', 'it', 'this', 'the alert', 'the notification']:
            return subscriptions[0] if subscriptions else None
        
        return None
    
    async def _get_recent_subscription_target(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str
    ) -> Optional[str]:
        """Get target from recent subscription creation in session"""
        try:
            chat_service = get_chat_session_service()
            messages = await chat_service.get_session_messages(
                session_id=session_id,
                user_id=user_id,
                tenant_id=tenant_id,
                limit=20
            )
            
            # Look for recent subscription creation
            for msg in reversed(messages):
                if msg.role == 'assistant':
                    # Check if this was a subscription confirmation
                    if '✅ I\'ll' in msg.content and 'subscription_id' in msg.content:
                        # Extract name from message
                        match = re.search(r"✅ I'll (.+?) (?:when|daily|weekly|monthly|hourly)", msg.content)
                        if match:
                            return match.group(1)
            
            return None
        except:
            return None
