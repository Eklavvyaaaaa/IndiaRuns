import { CometChat } from '@cometchat/chat-sdk-javascript';

const APP_ID = import.meta.env.VITE_COMETCHAT_APP_ID;
const REGION = import.meta.env.VITE_COMETCHAT_REGION;
const AUTH_KEY = import.meta.env.VITE_COMETCHAT_AUTH_KEY;

let isInitialized = false;
let isLoggingIn = false;

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

export const CometChatService = {
  init: async () => {
    if (isInitialized) return;

    const appSetting = new CometChat.AppSettingsBuilder()
      .subscribePresenceForAllUsers()
      .setRegion(REGION)
      .autoEstablishSocketConnection(true)
      .build();

    try {
      await CometChat.init(APP_ID, appSetting);
      isInitialized = true;
      console.log('CometChat initialized');
      await CometChatService.ensureLoggedIn();
    } catch (error) {
      console.error('CometChat init failed:', error);
    }
  },

  ensureLoggedIn: async () => {
    if (isLoggingIn) return;
    isLoggingIn = true;

    try {
      const existing = await CometChat.getLoggedinUser();
      if (existing) {
        isLoggingIn = false;
        return;
      }

      try {
        await CometChat.login('recruiter', AUTH_KEY);
      } catch (e: any) {
        if (e.code === 'ERR_UID_NOT_FOUND') {
          const user = new CometChat.User('recruiter');
          user.setName('Senior Recruiter');
          await CometChat.createUser(user, AUTH_KEY);
          await CometChat.login('recruiter', AUTH_KEY);
        }
      }
    } catch (err) {
      console.error('Login failed:', err);
    } finally {
      isLoggingIn = false;
    }
  },

  joinOrCreateDiscussionRoom: async (candidateId: string, candidateName: string): Promise<string | null> => {
    const guid = `discuss_${candidateId.toLowerCase().replace(/[^a-z0-9_]/g, '')}`;
    const groupName = `Discussion: ${candidateName}`;

    try {
      await CometChat.getGroup(guid);
      try {
        await CometChat.joinGroup(guid, CometChat.GROUP_TYPE.PUBLIC, '');
      } catch (joinErr: any) {
        if (joinErr.code !== 'ERR_ALREADY_JOINED') {
          console.warn('Join warning:', joinErr.code);
        }
      }
      return guid;
    } catch {
      try {
        const group = new CometChat.Group(guid, groupName, CometChat.GROUP_TYPE.PUBLIC);
        await CometChat.createGroup(group);
        return guid;
      } catch (createErr) {
        console.error('Failed to create group:', createErr);
        return null;
      }
    }
  },

  /**
   * Generate a dynamic AI response using the candidate's real data.
   */
  generateAIResponse: (query: string, candidate: CandidateData): string => {
    const q = query.toLowerCase();
    const name = candidate.anonymized_name;
    const scores = candidate.scores;
    const bs = candidate.blindspot;

    // Find top 3 and bottom 3 scores
    const scoreEntries = Object.entries(scores).filter(([k]) => k !== 'final_score' && k !== 'role_penalty');
    const sorted = [...scoreEntries].sort((a, b) => b[1] - a[1]);
    const top3 = sorted.slice(0, 3);
    const bottom3 = sorted.slice(-3).reverse();

    if (q.includes('risk') || q.includes('concern') || q.includes('weak')) {
      const weakAreas = bottom3.map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v.toFixed(1)}`).join(', ');
      const risks: string[] = [];
      if (candidate.is_honeypot) risks.push('⚠️ This candidate is flagged as a potential honeypot — timeline or skill inconsistencies detected.');
      if (bs.delta < 0) risks.push(`Their capability score (${bs.capability_score.toFixed(1)}) is lower than their ATS score (${bs.ats_score.toFixed(1)}), suggesting possible keyword inflation.`);
      risks.push(`Weakest scoring areas: ${weakAreas}.`);
      return `🤖 **AI Copilot — Risk Analysis for ${name}:**\n${risks.map(r => `• ${r}`).join('\n')}`;
    }

    if (q.includes('gem') || q.includes('hidden') || q.includes('potential')) {
      if (bs.is_hidden_gem) {
        return `🤖 **AI Copilot — Hidden Gem Analysis:**\n• ${name} IS a Hidden Gem! Their ATS score is ${bs.ats_score.toFixed(1)} but their true capability score is ${bs.capability_score.toFixed(1)} — a delta of +${bs.delta.toFixed(1)} points.\n• This means traditional keyword-based systems would underrate this candidate.\n• Their strongest signals: ${top3.map(([k, v]) => `${k.replace(/_/g, ' ')} (${v.toFixed(1)})`).join(', ')}.`;
      } else {
        return `🤖 **AI Copilot:** ${name} is not flagged as a Hidden Gem. Their ATS score (${bs.ats_score.toFixed(1)}) and capability score (${bs.capability_score.toFixed(1)}) are closely aligned (delta: ${bs.delta.toFixed(1)}).`;
      }
    }

    if (q.includes('interview') || q.includes('question') || q.includes('ask')) {
      const weakSkills = bottom3.map(([k]) => k.replace(/_/g, ' '));
      const strongSkills = top3.map(([k]) => k.replace(/_/g, ' '));
      return `🤖 **AI Copilot — Interview Questions for ${name}:**\n1. "Your ${weakSkills[0]} score is relatively low. Can you walk us through your experience in this area?"\n2. "You scored highly in ${strongSkills[0]}. Can you describe a specific project where you applied this?"\n3. "How would you approach bridging your gap in ${weakSkills[1]} if you joined our team?"\n4. "Describe a production system you've built end-to-end and the tradeoffs you made."`;
    }

    if (q.includes('compare') || q.includes('vs') || q.includes('versus')) {
      return `🤖 **AI Copilot:** To compare ${name} with another candidate, please use the Candidate Comparison page. ${name}'s final score is ${scores.final_score?.toFixed(1)}, with top strengths in ${top3.map(([k, v]) => `${k.replace(/_/g, ' ')} (${v.toFixed(1)})`).join(', ')}.`;
    }

    if (q.includes('strength') || q.includes('strong') || q.includes('good')) {
      const strongAreas = top3.map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v.toFixed(1)}`).join(', ');
      return `🤖 **AI Copilot — Strengths for ${name}:**\n• Final Score: ${scores.final_score?.toFixed(1)}\n• Top scoring areas: ${strongAreas}\n• ${candidate.reasoning[0] || 'Strong overall profile.'}`;
    }

    if (q.includes('summary') || q.includes('overview') || q.includes('tell me about')) {
      return `🤖 **AI Copilot — Summary for ${name}:**\n• Title: ${candidate.title}\n• Final Score: ${scores.final_score?.toFixed(1)}\n• Top strengths: ${top3.map(([k, v]) => `${k.replace(/_/g, ' ')} (${v.toFixed(1)})`).join(', ')}\n• Areas to probe: ${bottom3.map(([k, v]) => `${k.replace(/_/g, ' ')} (${v.toFixed(1)})`).join(', ')}\n• Hidden Gem: ${bs.is_hidden_gem ? 'Yes ✅' : 'No'}\n• Honeypot Risk: ${candidate.is_honeypot ? '⚠️ Yes' : 'Clean ✅'}`;
    }

    // Default: give a comprehensive overview
    return `🤖 **AI Copilot — ${name}:**\n• Score: ${scores.final_score?.toFixed(1)} | Title: ${candidate.title}\n• Strengths: ${top3.map(([k, v]) => `${k.replace(/_/g, ' ')} (${v.toFixed(1)})`).join(', ')}\n• Gaps: ${bottom3.map(([k, v]) => `${k.replace(/_/g, ' ')} (${v.toFixed(1)})`).join(', ')}\n• ${candidate.reasoning[0] || ''}\nTry asking: @AI risks, @AI interview questions, @AI hidden gem`;
  }
};
