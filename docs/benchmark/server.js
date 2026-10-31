const {WebSocketServer}=require("ws"); const http=require("http");
const port=+process.argv[2];
const srv=http.createServer((q,r)=>{r.end("ok")});
const wss=new WebSocketServer({server:srv,path:"/ws"});
const msg=JSON.stringify({type:"chat",name:"Mira",text:"x".repeat(250)});
setInterval(()=>{for(const c of wss.clients) c.send(msg)},200);
srv.listen(port,"127.0.0.1");
