package main
import ("context";"fmt";"net/http";"os";"sync";"time";"github.com/coder/websocket")
var mu sync.Mutex
var clients = map[*websocket.Conn]struct{}{}
func main(){
  msg:=[]byte(`{"type":"chat","name":"Mira","text":"`+string(make([]byte,0))+`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}`)
  http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request){ fmt.Fprint(w,"ok") })
  http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request){
    c,err:=websocket.Accept(w,r,nil); if err!=nil {return}
    mu.Lock(); clients[c]=struct{}{}; mu.Unlock()
    ctx:=c.CloseRead(r.Context()); <-ctx.Done()
    mu.Lock(); delete(clients,c); mu.Unlock()
  })
  go func(){ for range time.Tick(200*time.Millisecond){ mu.Lock(); for c:=range clients { ctx,cancel:=context.WithTimeout(context.Background(),time.Second); c.Write(ctx,websocket.MessageText,msg); cancel() }; mu.Unlock() } }()
  http.ListenAndServe("127.0.0.1:"+os.Args[1],nil)
}
