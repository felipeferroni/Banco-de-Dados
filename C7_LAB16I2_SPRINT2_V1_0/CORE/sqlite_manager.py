import sqlite3

def export_sqlite(path,tables):
    with sqlite3.connect(path) as con:
        for name,df in tables.items(): df.to_sql(name,con,if_exists='replace',index=False)
        con.execute('CREATE INDEX IF NOT EXISTS idx_stats_gene ON gene_statistics(gene_id)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_dict_gene ON gene_dictionary_enriched(gene_id)')
