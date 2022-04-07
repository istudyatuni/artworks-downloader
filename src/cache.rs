#![allow(unused)]

use rusqlite::Connection;
use serde_json::Value;

const CACHE_DB: &str = ".cache.db";

const INIT_QUERY: &str = "CREATE TABLE IF NOT EXISTS cache (
    key TEXT NOT NULL PRIMARY KEY,
    value TEXT
)";
const INSERT_QUERY: &str = "INSERT OR IGNORE
    INTO cache (key, value)
    VALUES (:key, :value)";
const SELECT_QUERY: &str = "SELECT value FROM cache WHERE key = :key";
const DELETE_QUERY: &str = "DELETE FROM cache WHERE key = :key";

pub struct Cache {
    connection: Connection,
}

fn init(conn: &Connection) {
    conn.execute(INIT_QUERY, []).unwrap();
}
macro_rules! key {
    ($slug:expr,$key:expr) => {
        format!("{}:{}", $slug, $key).as_str()
    };
}

impl Cache {
    pub fn new() -> Self {
        let conn = Connection::open(CACHE_DB);
        match conn {
            Ok(conn) => {
                init(&conn);
                Self { connection: conn }
            }
            Err(e) => panic!("{}", e),
        }
    }
    pub fn insert(&self, slug: &str, key: &str, value: &str) {
        self.connection
            .execute(
                INSERT_QUERY,
                &[(":key", key!(slug, key)), (":value", value)],
            )
            .unwrap();
    }
    pub fn insert_json(&self, slug: &str, key: &str, value: Value) {
        self.insert(slug, key, value.to_string().as_str())
    }
    pub fn select(&self, slug: &str, key: &str) -> Option<String> {
        self.connection
            .query_row(SELECT_QUERY, &[(":key", key!(slug, key))], |row| row.get(0))
            .unwrap_or(None)
    }
    pub fn select_json(&self, slug: &str, key: &str) -> Option<Value> {
        match self.select(slug, key) {
            Some(value) => serde_json::from_str(value.as_str())
                .expect(format!("Couldn't parse cached JSON for key {key}").as_str()),
            None => None,
        }
    }
    pub fn delete(&self, slug: &str, key: &str) {
        self.connection
            .execute(DELETE_QUERY, &[(":key", key!(slug, key))])
            .expect("Couldn't delete from cache");
    }
}
