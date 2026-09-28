alter table public.sales_leads
    add column if not exists sent_at timestamptz,
    add column if not exists reply_at timestamptz,
    add column if not exists sender_email text,
    add column if not exists message_id text;

create index if not exists sales_leads_contacted_idx
    on public.sales_leads(status, sent_at desc);
