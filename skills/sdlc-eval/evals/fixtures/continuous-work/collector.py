"""Small source fixture, intentionally retains a reported defect for evaluation."""
def normalize(rows):
    return [dict(row) for row in rows if row.get('amount_cents')]


def store(db, rows):
    for row in normalize(rows):
        db.execute('INSERT INTO observations(source,external_id,observed_day,amount_cents) VALUES (?,?,?,?)',
                   (row['source'], row['external_id'], row['observed_day'], row['amount_cents']))
    db.commit()
