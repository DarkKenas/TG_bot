from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date

class RegistrationForm(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str
    password: str = Field(min_length=8)
    password_confirm: str
    birth_date: date
    terms_accepted: bool
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()
    
    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_validator('birth_date')
    @classmethod
    def check_age(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('Must be at least 18 years old')
        return v
    
    @field_validator('terms_accepted')
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError('You must accept the terms')
        return v
    
    @model_validator(mode='after')
    def passwords_match(self) -> 'RegistrationForm':
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self

# Обработка ошибок валидации
from pydantic import ValidationError

try:
    form = RegistrationForm(
        username="alex123",
        email="alex@example.com",
        password="SecurePass1",
        password_confirm="SecurePass2",  # не совпадает!
        birth_date="2010-01-01",  # слишком молодой!
        terms_accepted=False  # не принял!
    )
except ValidationError as e:
    # print(e.errors())
    # [
    #   {'type': 'value_error', 'loc': ('birth_date',), 'msg': 'Must be at least 18...'},
    #   {'type': 'value_error', 'loc': ('terms_accepted',), 'msg': 'You must accept...'},
    #   {'type': 'value_error', 'loc': (), 'msg': 'Passwords do not match'}
    # ]
    
    # Красивый вывод ошибок
    for error in e.errors():
        field = '.'.join(str(x) for x in error['loc']) or 'form'
        print(f"{field}: {error['msg']}")