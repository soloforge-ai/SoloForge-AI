// Disposable PostgreSQL/WASM bridge for offline integration tests only.
// No HTTP server, project credentials, persistent DB, extensions or network.
import fs from 'node:fs';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

globalThis.fetch = () => { throw new Error('Network forbidden in offline tests'); };
const { PGlite } = await import(pathToFileURL(process.env.OWNER_V2_TEST_PGLITE).href);
const db = new PGlite();
await db.exec('create role anon; create role authenticated; create role service_role bypassrls;');
for (const migration of process.argv.slice(2)) {
  await db.exec(fs.readFileSync(migration, 'utf8'));
}
console.log(JSON.stringify({ready: true}));
for await (const line of readline.createInterface({input: process.stdin})) {
  const {sql, params = [], role = 'postgres'} = JSON.parse(line);
  try {
    if (!['postgres', 'anon', 'authenticated', 'service_role'].includes(role)) throw new Error('Invalid role');
    const result = await db.transaction(async tx => {
      await tx.exec(`set local role ${role}`);
      return await tx.query(sql, params);
    });
    console.log(JSON.stringify({rows: result.rows}));
  } catch (error) {
    console.log(JSON.stringify({error: error.message, code: error.code}));
  }
}
await db.close();
