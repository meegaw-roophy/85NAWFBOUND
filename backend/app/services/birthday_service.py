"""
VEKTRA Birthday Service
=======================
Handles birthday detection and high-res image generation for viral marketing.
"""

import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import User
from app.services.visual_generator import visual_generator


class BirthdayService:
    """Handles birthday-related operations."""
    
    async def check_birthdays_today(self, db: AsyncSession) -> list:
        """
        Find all users whose birthday is today.
        Returns list of user objects.
        """
        today = datetime.datetime.utcnow().date()
        month, day = today.month, today.day
        
        result = await db.execute(
            select(User).where(
                User.dob.isnot(None),
                User.dob != ''
            )
        )
        users = result.scalars().all()
        
        birthday_users = []
        for user in users:
            if user.dob:
                if user.dob.month == month and user.dob.day == day:
                    birthday_users.append(user)
        
        return birthday_users
    
    async def generate_birthday_content(self, user: User) -> dict:
        """
        Generate birthday image and message for a user.
        Returns dict with image_base64 and message.
        """
        if not user.dob:
            return None
        
        # Calculate age
        today = datetime.datetime.utcnow().date()
        age = today.year - user.dob.year - ((today.month, today.day) < (user.dob.month, user.dob.day))
        
        # Generate high-res image
        image_bytes = visual_generator.generate_birthday_image(
            user_name=user.full_name or user.username,
            age=age,
            width=1920,
            height=1080
        )
        
        image_base64 = visual_generator.encode_image_to_base64(image_bytes)
        
        # Generate personalized message
        message = f"Happy {age}th Birthday, {user.full_name or user.username}! 🎉\n\n"
        message += "Another year closer to your North Star. Keep tracking your trajectory with VEKTRA.\n\n"
        message += "Vector = Magnitude × Direction"
        
        return {
            'user_id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'age': age,
            'image_base64': image_base64,
            'message': message,
            'generated_at': datetime.datetime.utcnow().isoformat()
        }
    
    async def send_birthday_wishes(self, db: AsyncSession) -> list:
        """
        Check for birthdays today and generate content for all.
        Returns list of birthday content dicts.
        """
        birthday_users = await self.check_birthdays_today(db)
        results = []
        
        for user in birthday_users:
            content = await self.generate_birthday_content(user)
            if content:
                results.append(content)
        
        return results


birthday_service = BirthdayService()
