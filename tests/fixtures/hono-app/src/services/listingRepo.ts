export async function listActive(db: D1Database) {
  const { results } = await db.prepare("SELECT * FROM listings WHERE status = 'active'").all()
  return results
}
