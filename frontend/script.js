document.addEventListener("DOMContentLoaded", () => {

const chatInput = document.getElementById("chat-input")
const sendBtn = document.getElementById("send-btn")
const chatMessages = document.getElementById("chat-messages")
const questionsAnsweredEl = document.getElementById("questions-answered")

let questionsAnswered = 0


chatInput.addEventListener("keypress", e => {

if(e.key==="Enter" && chatInput.value.trim()!==""){
sendMessage()
}

})

sendBtn.addEventListener("click",()=>{

if(chatInput.value.trim()!==""){
sendMessage()
}

})


function sendMessage(){

const message = chatInput.value.trim()
if(!message) return

addMessage(message,"user")
chatInput.value=""

setChatDisabled(true)

const typingId="typing-"+Date.now()
addTypingIndicator(typingId)

fetch("/api/chat",{

method:"POST",
headers:{ "Content-Type":"application/json" },
body:JSON.stringify({ message })

})

.then(res=>res.json())
.then(data=>{

removeTypingIndicator(typingId)

addMessage(data.answer,"bot")

if(data.sources && data.sources.length>0){

addSources(data.sources)

}

questionsAnswered++
questionsAnsweredEl.textContent=questionsAnswered

})

.catch(()=>{

removeTypingIndicator(typingId)
addMessage("Error retrieving answer.","bot")

})

.finally(()=>{

setChatDisabled(false)
chatInput.focus()

})

}


function addMessage(text,sender){

const msgDiv=document.createElement("div")
msgDiv.className=`message ${sender}`

const avatar=document.createElement("div")
avatar.className="msg-avatar"

avatar.innerHTML= sender==="bot"
? '<i class="ph-fill ph-robot"></i>'
: '<i class="ph-fill ph-user"></i>'

const bubble=document.createElement("div")
bubble.className="msg-bubble"

bubble.textContent=text
bubble.innerHTML=bubble.innerHTML.replace(/\n/g,"<br>")

msgDiv.appendChild(avatar)
msgDiv.appendChild(bubble)

chatMessages.appendChild(msgDiv)

scrollToBottom()

}


function addSources(sources){

const msgDiv=document.createElement("div")
msgDiv.className="message bot"

const avatar=document.createElement("div")
avatar.className="msg-avatar"
avatar.innerHTML='<i class="ph-fill ph-info"></i>'

const bubble=document.createElement("div")
bubble.className="msg-bubble sources-container"

sources.forEach(src=>{

const item=document.createElement("div")
item.className="source-item"
item.textContent="📄 "+src

bubble.appendChild(item)

})

msgDiv.appendChild(avatar)
msgDiv.appendChild(bubble)

chatMessages.appendChild(msgDiv)

scrollToBottom()

}


function addTypingIndicator(id){

const msg=document.createElement("div")
msg.className="message bot"
msg.id=id

msg.innerHTML=`

<div class="msg-avatar"><i class="ph-fill ph-robot"></i></div>

<div class="msg-bubble typing-indicator">

<span></span>
<span></span>
<span></span>

</div>

`

chatMessages.appendChild(msg)

scrollToBottom()

}


function removeTypingIndicator(id){

const el=document.getElementById(id)
if(el) el.remove()

}


function setChatDisabled(state){

chatInput.disabled=state
sendBtn.disabled=state

}


function scrollToBottom(){

chatMessages.scrollTop=chatMessages.scrollHeight

}

})