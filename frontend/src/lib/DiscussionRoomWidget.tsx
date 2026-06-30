import React, { useState, useEffect, useRef } from 'react';
import { CometChat } from '@cometchat/chat-sdk-javascript';
import { X, Send, Users } from 'lucide-react';
import { CometChatService } from './CometChatService';

interface DiscussionRoomWidgetProps {
  guid: string;
  candidateName: string;
  onClose: () => void;
}

export default function DiscussionRoomWidget({ guid, candidateName, onClose }: DiscussionRoomWidgetProps) {
  const [messages, setMessages] = useState<CometChat.BaseMessage[]>([]);
  const [text, setText] = useState('');
  const [currentUser, setCurrentUser] = useState<CometChat.User | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const listenerID = `UNIQUE_LISTENER_ID_GROUP_${guid}`;

  useEffect(() => {
    CometChat.getLoggedinUser().then(user => setCurrentUser(user));

    const messagesRequest = new CometChat.MessagesRequestBuilder()
      .setGUID(guid)
      .setLimit(50)
      .build();

    messagesRequest.fetchPrevious().then(
      msgs => {
        setMessages(msgs);
        scrollToBottom();
      },
      error => console.log('Message fetching failed', error)
    );

    CometChat.addMessageListener(
      listenerID,
      new CometChat.MessageListener({
        onTextMessageReceived: (textMessage: CometChat.TextMessage) => {
          if (textMessage.getReceiverId() === guid && textMessage.getReceiverType() === CometChat.RECEIVER_TYPE.GROUP) {
            setMessages(prev => [...prev, textMessage]);
            scrollToBottom();
          }
        }
      })
    );

    return () => {
      CometChat.removeMessageListener(listenerID);
    };
  }, [guid]);

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    const messageText = text;
    const receiverType = CometChat.RECEIVER_TYPE.GROUP;
    const textMessage = new CometChat.TextMessage(guid, messageText, receiverType);

    try {
      setText(''); // Optimistic clear
      const msg = await CometChat.sendMessage(textMessage);
      setMessages(prev => [...prev, msg]);
      scrollToBottom();
      
      // AI check
      if (messageText.includes('@AI')) {
        setTimeout(() => {
          CometChatService.sendBotResponse(guid, messageText, candidateName);
        }, 1000);
      }
    } catch (error) {
      console.log('Message sending failed', error);
      setText(messageText); // Revert on failure
    }
  };

  return (
    <div className="fixed bottom-4 right-4 w-96 h-[500px] bg-slate-900 border border-slate-700 rounded-lg shadow-2xl flex flex-col z-50 overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center bg-indigo-900/50 p-4 border-b border-indigo-700">
        <div>
          <h3 className="font-semibold text-slate-200 flex items-center gap-2">
            <Users size={18} className="text-indigo-400" />
            Discussion: {candidateName}
          </h3>
          <p className="text-xs text-indigo-300 mt-1">Recruiter, Hiring Mgr, CTO, AI</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors bg-slate-800 rounded-full p-1.5 border border-slate-700">
          <X size={18} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950">
        {messages.length === 0 ? (
          <div className="text-center text-slate-500 text-sm mt-10">
            No discussion yet. Type "@AI" to ask for insights!
          </div>
        ) : (
          messages.map((msg, i) => {
            if (!(msg instanceof CometChat.TextMessage)) return null;
            
            const sender = msg.getSender();
            const isMe = sender.getUid() === currentUser?.getUid();
            const isAI = sender.getUid() === 'ai_assistant';
            
            return (
              <div key={i} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                {!isMe && (
                  <span className={`text-xs mb-1 font-semibold ${isAI ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {sender.getName()}
                  </span>
                )}
                <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm shadow-md ${
                  isMe ? 'bg-indigo-600 text-white' : 
                  isAI ? 'bg-emerald-900/40 border border-emerald-500/30 text-emerald-100' : 
                  'bg-slate-800 text-slate-200 border border-slate-700'
                }`}>
                  {msg.getText()}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="p-3 bg-slate-800 border-t border-slate-700 flex items-center gap-2">
        <input
          type="text"
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Type a message (use @AI for help)..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <button type="submit" className="bg-indigo-600 p-2 rounded-md text-white hover:bg-indigo-500 transition-colors shadow-lg shadow-indigo-900/20" disabled={!text.trim()}>
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
