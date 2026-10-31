use axum::{extract::ws::{Message, WebSocket, WebSocketUpgrade}, routing::get, Router, extract::State};
use tokio::sync::broadcast;
#[tokio::main(flavor = "current_thread")]
async fn main() {
    let port = std::env::args().nth(1).unwrap();
    let (tx, _) = broadcast::channel::<String>(16);
    let t2 = tx.clone();
    tokio::spawn(async move {
        let msg = format!("{{\"type\":\"chat\",\"name\":\"Mira\",\"text\":\"{}\"}}", "x".repeat(250));
        let mut i = tokio::time::interval(std::time::Duration::from_millis(200));
        loop { i.tick().await; let _ = t2.send(msg.clone()); }
    });
    let app = Router::new().route("/", get(|| async { "ok" })).route("/ws", get(ws)).with_state(tx);
    let l = tokio::net::TcpListener::bind(format!("127.0.0.1:{port}")).await.unwrap();
    axum::serve(l, app).await.unwrap();
}
async fn ws(u: WebSocketUpgrade, State(tx): State<broadcast::Sender<String>>) -> axum::response::Response {
    u.on_upgrade(move |mut s: WebSocket| async move {
        let mut rx = tx.subscribe();
        while let Ok(m) = rx.recv().await { if s.send(Message::text(m)).await.is_err() { break; } }
    })
}
