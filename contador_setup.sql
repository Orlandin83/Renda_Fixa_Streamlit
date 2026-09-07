CREATE TABLE IF NOT EXISTS public.contador_simulacoes (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    total BIGINT NOT NULL DEFAULT 0 CHECK (total >= 0)
);
INSERT INTO public.contador_simulacoes (id, total)
VALUES (1, 0) ON CONFLICT (id) DO NOTHING;
-- Impede acesso via APIs públicas do Supabase; use conexão de servidor autorizada.
ALTER TABLE public.contador_simulacoes ENABLE ROW LEVEL SECURITY;
