-- 002 日结触顶标记：normal/capped/unknown
-- 已有数据默认 normal；旧日结无标记的历史数据可由业务手工修订为 unknown。
ALTER TABLE public.daily_volumes
    ADD COLUMN mark character varying(10);

UPDATE public.daily_volumes SET mark = 'normal' WHERE mark IS NULL;

ALTER TABLE public.daily_volumes
    ALTER COLUMN mark SET DEFAULT 'normal',
    ALTER COLUMN mark SET NOT NULL;
