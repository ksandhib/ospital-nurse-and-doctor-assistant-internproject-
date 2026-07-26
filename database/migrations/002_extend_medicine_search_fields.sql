USE ai_clinicos;

SET @schema_name = DATABASE();

SET @sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = @schema_name AND table_name = 'medicines' AND column_name = 'symptoms_keywords') = 0, 'ALTER TABLE medicines ADD COLUMN symptoms_keywords TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = @schema_name AND table_name = 'medicines' AND column_name = 'search_keywords') = 0, 'ALTER TABLE medicines ADD COLUMN search_keywords TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = @schema_name AND table_name = 'medicines' AND column_name = 'medicine_description') = 0, 'ALTER TABLE medicines ADD COLUMN medicine_description TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = @schema_name AND table_name = 'medicines' AND column_name = 'clinical_notes') = 0, 'ALTER TABLE medicines ADD COLUMN clinical_notes TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = @schema_name AND table_name = 'medicines' AND column_name = 'common_diseases') = 0, 'ALTER TABLE medicines ADD COLUMN common_diseases TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = @schema_name AND table_name = 'medicines' AND column_name = 'alternative_medicines') = 0, 'ALTER TABLE medicines ADD COLUMN alternative_medicines TEXT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
