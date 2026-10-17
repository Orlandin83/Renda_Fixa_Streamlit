-- Histórico ANBIMA: executar como administrador no projeto renda-fixa.
create extension if not exists http with schema extensions;
create extension if not exists pg_cron;
create schema if not exists curvas_privado;
revoke all on schema curvas_privado from public, anon, authenticated;

create table if not exists public.curvas_anbima (
    data_referencia date not null,
    indexador text not null check (indexador in ('PREFIXADOS', 'IPCA')),
    b1 double precision not null, b2 double precision not null,
    b3 double precision not null, b4 double precision not null,
    l1 double precision not null check (l1 > 0 and l1 < 'Infinity'::float8),
    l2 double precision not null check (l2 > 0 and l2 < 'Infinity'::float8),
    ultimo_vertice_du integer check (ultimo_vertice_du > 0),
    coletado_em timestamptz not null default now(),
    primary key (data_referencia, indexador),
    check (b1 > '-Infinity'::float8 and b1 < 'Infinity'::float8
       and b2 > '-Infinity'::float8 and b2 < 'Infinity'::float8
       and b3 > '-Infinity'::float8 and b3 < 'Infinity'::float8
       and b4 > '-Infinity'::float8 and b4 < 'Infinity'::float8)
);
alter table public.curvas_anbima enable row level security;
revoke all on public.curvas_anbima from anon, authenticated;
grant select on public.curvas_anbima to anon, authenticated;
create policy "Leitura das curvas de mercado" on public.curvas_anbima
    for select to anon, authenticated using (true);

-- Função privada, sem SECURITY DEFINER e sem acesso pelas APIs públicas.
create or replace function curvas_privado.coletar(p_data date)
returns integer language plpgsql security invoker set search_path = '' as $$
declare
    resposta record;
    linha text;
    campos text[];
    quantidade integer := 0;
    na_ettj boolean := false;
    max_pre integer;
    max_ipca integer;
    vertice integer;
begin
    if p_data > (now() at time zone 'America/Sao_Paulo')::date then
        raise exception 'Data futura';
    end if;
    perform extensions.http_set_curlopt('CURLOPT_TIMEOUT_MS', '15000');
    select * into resposta from extensions.http_post(
        'https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp',
        'Idioma=PT&saida=csv&Dt_Ref=' || to_char(p_data, 'DD/MM/YYYY'),
        'application/x-www-form-urlencoded');
    if resposta.status <> 200 then
        raise exception 'ANBIMA HTTP %', resposta.status;
    end if;
    -- Nunca atribuir a uma data os parâmetros de outra publicação.
    if split_part(resposta.content, ';', 1) <> to_char(p_data, 'DD/MM/YYYY') then
        return 0;
    end if;
    for linha in select regexp_split_to_table(resposta.content, E'\r?\n') loop
        campos := string_to_array(linha, ';');
        if campos[1] in ('PREFIXADOS', 'IPCA') then
            if cardinality(campos) < 7 then raise exception 'Parâmetros incompletos'; end if;
            insert into public.curvas_anbima (data_referencia,indexador,b1,b2,b3,b4,l1,l2)
            values (p_data, campos[1], replace(campos[2],',','.')::float8,
                replace(campos[3],',','.')::float8, replace(campos[4],',','.')::float8,
                replace(campos[5],',','.')::float8, replace(campos[6],',','.')::float8,
                replace(campos[7],',','.')::float8)
            on conflict (data_referencia,indexador) do update set
                b1=excluded.b1,b2=excluded.b2,b3=excluded.b3,b4=excluded.b4,
                l1=excluded.l1,l2=excluded.l2,coletado_em=now();
            quantidade := quantidade + 1;
        end if;
    end loop;
    if quantidade = 0 then return 0; end if;
    if quantidade <> 2 then raise exception 'Publicação incompleta: % curvas', quantidade; end if;
    -- Limites da tabela ETTJ publicada, sem usar a tabela Circular 3.361.
    for linha in select regexp_split_to_table(resposta.content, E'\r?\n') loop
        campos := string_to_array(linha, ';');
        if linha like 'Vertices;ETTJ IPCA;ETTJ PREF;%' then
            na_ettj := true;
            continue;
        end if;
        if na_ettj then
            if campos[1] !~ '^[0-9.]+$' then exit; end if;
            vertice := replace(campos[1], '.', '')::integer;
            if nullif(trim(campos[2]), '') is not null then
                max_ipca := greatest(max_ipca, vertice);
            end if;
            if nullif(trim(campos[3]), '') is not null then
                max_pre := greatest(max_pre, vertice);
            end if;
        end if;
    end loop;
    if max_pre is null or max_ipca is null then
        raise exception 'Limites da publicação ETTJ não encontrados';
    end if;
    update public.curvas_anbima set ultimo_vertice_du =
        case when indexador = 'PREFIXADOS' then max_pre else max_ipca end
        where data_referencia = p_data;
    return quantidade;
end;
$$;
revoke all on function curvas_privado.coletar(date) from public, anon, authenticated;

create or replace function curvas_privado.atualizar()
returns integer language plpgsql security invoker set search_path = '' as $$
declare d date; total integer := 0;
begin
    -- Reconsulta uma semana para recuperar atrasos e revisões da publicação.
    for d in select ((now() at time zone 'America/Sao_Paulo')::date - n)
             from generate_series(0, 7) n loop
        if extract(isodow from d) <= 5 then
            total := total + curvas_privado.coletar(d);
        end if;
    end loop;
    return total;
end;
$$;
revoke all on function curvas_privado.atualizar() from public, anon, authenticated;
-- 21h30 e 23h30 de Brasília (UTC-3), todos os dias; recupera atrasos.
select cron.schedule('curvas-anbima-diaria', '30 0,2 * * *',
                     'select curvas_privado.atualizar();');
-- Este projeto não expunha schemas na Data API. Public contém só curvas_anbima.
alter role authenticator set pgrst.db_schemas = 'public';
notify pgrst, 'reload config';
notify pgrst, 'reload schema';
