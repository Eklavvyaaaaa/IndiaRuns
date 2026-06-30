import React, { useState, useEffect, useRef } from 'react';
import { CometChat } from '@cometchat/chat-sdk-javascript';
import { X, Send, Users, Bot } from 'lucide-react';
import { CometChatService } from './CometChatService';

interface CandidateData {
  candidate_id: string;
  anonymized_name: string;
  title: string;
  summary: string;
  scores: Record<string, number>;
  blindspot: { ats_score: number; capability_score: number; delta: number; is_hidden_gem: boolean };
  reasoning: string[];
  is_honeypot: boolean;
}

interface DiscussionRoomWidgetProps {
  guid: string;
  candidate: CandidateData;
  onClose: () => void;
}

interface LocalMessage {
  id: string;
  text: string;
  senderName: string;
  senderUid: string;
  isAI: boolean;
  timestamp: number;
}

export default function DiscussionRoomWidget({ guid, candidate, onClose }: DiscussionRoomWidgetProps) {
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [text, setText] = useState('');
  const [currentUserUid, setCurrentUserUid] = useState('recruiter');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const listenerID = `LISTENER_${guid}_${Date.now()}`;

  useEffect(() => {
    CometChat.getLoggedinUser().then(user => {
      if (user) setCurrentUserUid(user.getUid());
    });

    // Fetch previous messages
    const req = new CometChat.MessagesRequestBuilder()
      .setGUID(guid)
      .setLimit(50)
      .build();

    req.fetchPrevious().then(
      (msgs) => {
        const mapped: LocalMessage[] = msgs
          .filter((m): m is CometChat.TextMessage => m instanceof CometChat.TextMessage)
          .map((m, i) => ({
            id: `hist_${i}`,
            text: m.getText(),
            senderName: m.getSender().getName(),
            senderUid: m.getSender().getUid(),
            isAI: m.getSender().getUid() === 'ai_assistant',
            timestamp: m.getSentAt(),
          }));
        setMessages(mapped);
        scrollToBottom();
      },
      (err) => console.error('Fetch messages failed:', err)
    );

    // Real-time listener
    CometChat.addMessageListener(
      listenerID,
      new CometChat.MessageListener({
        onTextMessageReceived: (msg: CometChat.TextMessage) => {
          if (msg.getReceiverType() === CometChat.RECEIVER_TYPE.GROUP && msg.getReceiverId() === guid) {
            setMessages(prev => [...prev, {
              id: `rt_${Date.now()}`,
              text: msg.getText(),
              senderName: msg.getSender().getName(),
              senderUid: msg.getSender().getUid(),
              isAI: false,
              timestamp: msg.getSentAt(),
            }]);
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
    setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    const messageText = text.trim();
    setText('');

    // Send to CometChat group
    try {
      const textMessage = new CometChat.TextMessage(guid, messageText, CometChat.RECEIVER_TYPE.GROUP);
      await CometChat.sendMessage(textMessage);
    } catch (err) {
      console.error('CometChat send failed (showing locally):', err);
    }

    // Always show locally
    setMessages(prev => [...prev, {
      id: `sent_${Date.now()}`,
      text: messageText,
      senderName: 'You',
      senderUid: currentUserUid,
      isAI: false,
      timestamp: Date.now() / 1000,
    }]);
    scrollToBottom();

    // If user mentioned @AI, generate a dynamic response from real candidate data
    if (messageText.includes('@AI')) {
      setTimeout(() => {
        const aiResponse = CometChatService.generateAIResponse(messageText, candidate);
        setMessages(prev => [...prev, {
          id: `ai_${Date.now()}`,
          text: aiResponse,
          senderName: 'RedRob AI Copilot',
          senderUid: 'ai_assistant',
          isAI: true,
          timestamp: Date.now() / 1000,
        }]);
        scrollToBottom();
      }, 800);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 w-96 h-[500px] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex flex-col z-50 overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center bg-gradient-to-r from-indigo-900/80 to-purple-900/60 p-4 border-b border-indigo-700/50">
        <div>
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Users size={18} className="text-indigo-300" />
            {candidate.anonymized_name}
          </h3>
          <p className="text-xs text-indigo-300/80 mt-0.5">
            {candidate.title} • Score: {candidate.scores.final_score?.toFixed(1)}
          </p>
        </div>
        <button onClick={onClose} className="text-slate-300 hover:text-white transition-colors bg-white/10 hover:bg-white/20 rounded-full p-1.5">
          <X size={16} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-950/80">
        {messages.length === 0 ? (
          <div className="text-center text-slate-500 text-sm mt-10 space-y-2">
            <Bot size={32} className="mx-auto text-indigo-500/50" />
            <p>Start discussing {candidate.anonymized_name}</p>
            <p className="text-xs text-slate-600">
              Try: <span className="text-indigo-400 font-mono">@AI risks</span> • <span className="text-indigo-400 font-mono">@AI interview questions</span> • <span className="text-indigo-400 font-mono">@AI hidden gem</span>
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isMe = msg.senderUid === currentUserUid;

            return (
              <div key={msg.id} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                {!isMe && (
                  <span className={`text-xs mb-1 font-semibold ${msg.isAI ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {msg.isAI && '🤖 '}{msg.senderName}
                  </span>
                )}
                <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed whitespace-pre-line ${
                  isMe
                    ? 'bg-indigo-600 text-white'
                    : msg.isAI
                    ? 'bg-emerald-900/30 border border-emerald-600/30 text-emerald-100'
                    : 'bg-slate-800 text-slate-200 border border-slate-700'
                }`}>
                  {msg.text}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="p-3 bg-slate-800/90 border-t border-slate-700 flex items-center gap-2">
        <input
          type="text"
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Type @AI risks, @AI strengths..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
        />
        <button
          type="submit"
          disabled={!text.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed p-2 rounded-lg text-white transition-colors"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
