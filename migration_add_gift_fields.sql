-- Миграция: добавление полей gift_text и gift_url в таблицу transfers
-- Дата: 2025-01-22
-- Описание: Добавляет поля для хранения предложений подарков

-- Добавляем поле gift_text (текстовое поле для описания подарка)
ALTER TABLE transfers 
ADD COLUMN IF NOT EXISTS gift_text TEXT;

-- Добавляем поле gift_url (текстовое поле для ссылки на подарок)
ALTER TABLE transfers 
ADD COLUMN IF NOT EXISTS gift_url TEXT;

-- Комментарии к полям (опционально, для документации)
COMMENT ON COLUMN transfers.gift_text IS 'Текст предложения подарка';
COMMENT ON COLUMN transfers.gift_url IS 'URL предложения подарка';
