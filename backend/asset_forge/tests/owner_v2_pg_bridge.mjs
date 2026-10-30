// Disposable PostgreSQL/WASM bridge for offline integration tests only.
// No HTTP server, project credentials, persistent DB, extensions or network.
import fs from 'node:fs';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

globalThis.fetch = () => { throw new Error('Network forbidden in offline tests'); };
const { PGlite } = await import(pathToFileURL(process.env.OWNER_V2_TEST_PGLITE).href);
const db = new PGlite(process.argv[3]);
if (process.argv[4] !== 'reopen') {
    await db.exec('create role anon; create role authenticated; create role service_role bypassrls;');
    await db.exec(fs.readFileSync(process.argv[2], 'utf8'));
}
console.log(JSON.stringify({ready: true}));
for await (const line of readline.createInterface({input: process.stdin})) {
  const {sql, params = [], role = 'postgres', exec = false} = JSON.parse(line);
  try {
    if (!['postgres', 'anon', 'authenticated', 'service_role'].includes(role)) throw new Error('Invalid role');
    if (exec) {
      if (role !== 'postgres') throw new Error('Fixture DDL requires administrative role');
      await db.exec(sql);
      console.log(JSON.stringify({rows: []}));
      continue;
    }
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
