import { CometChat } from '@cometchat/chat-sdk-javascript';

const APP_ID = import.meta.env.VITE_COMETCHAT_APP_ID;
const REGION = import.meta.env.VITE_COMETCHAT_REGION;
const AUTH_KEY = import.meta.env.VITE_COMETCHAT_AUTH_KEY;

export const CometChatService = {
  init: async () => {
    const appSetting = new CometChat.AppSettingsBuilder()
      .subscribePresenceForAllUsers()
      .setRegion(REGION)
      .autoEstablishSocketConnection(true)
      .build();

    try {
      await CometChat.init(APP_ID, appSetting);
      console.log('CometChat Initialization completed successfully');
      
      // Auto-login as the recruiter for demo purposes
      await CometChatService.loginUser('recruiter', 'Senior Recruiter');
      await CometChatService.ensureSystemUsers();
    } catch (error) {
      console.log('CometChat Initialization failed with error:', error);
    }
  },

  loginUser: async (uid: string, name: string) => {
    try {
      const user = await CometChat.getLoggedinUser();
      if (!user || user.getUid() !== uid) {
        try {
          await CometChat.login(uid, AUTH_KEY);
        } catch (loginError: any) {
          if (loginError.code === 'ERR_UID_NOT_FOUND') {
            const newUser = new CometChat.User(uid);
            newUser.setName(name);
            await CometChat.createUser(newUser, AUTH_KEY);
            await CometChat.login(uid, AUTH_KEY);
          } else {
            throw loginError;
          }
        }
      }
    } catch (error) {
      console.log('CometChat login/create failed', error);
    }
  },

  ensureSystemUsers: async () => {
    const systemUsers = [
      { uid: 'hiring_manager', name: 'Hiring Manager' },
      { uid: 'cto', name: 'CTO' },
      { uid: 'ai_assistant', name: 'RedRob AI Copilot' }
    ];

    for (const u of systemUsers) {
      try {
        const newUser = new CometChat.User(u.uid);
        newUser.setName(u.name);
        await CometChat.createUser(newUser, AUTH_KEY);
      } catch (e: any) {
        // Ignore if already exists
        if (e.code !== 'ERR_UID_ALREADY_EXISTS') {
          console.log(`Failed to create system user ${u.uid}`, e);
        }
      }
    }
  },

  joinOrCreateDiscussionRoom: async (candidateId: string, candidateName: string) => {
    // Sanitize GUID or format for cometchat group id
    const guid = `discuss_${candidateId.toLowerCase().replace(/[^a-z0-9]/g, '')}`;
    const groupName = `Discussion: ${candidateName}`;
    const groupType = CometChat.GROUP_TYPE.PUBLIC;
    
    try {
      // Check if group exists by joining it
      await CometChat.joinGroup(guid, groupType, '');
      return guid;
    } catch (error: any) {
      if (error.code === 'ERR_GUID_NOT_FOUND' || error.code === 'ERR_GROUP_NOT_FOUND') {
        try {
          const group = new CometChat.Group(guid, groupName, groupType);
          await CometChat.createGroup(group);
          await CometChat.joinGroup(guid, groupType, '');
          
          // Add system users to the group
          const membersList = [
            new CometChat.GroupMember('hiring_manager', CometChat.GROUP_MEMBER_SCOPE.PARTICIPANT),
            new CometChat.GroupMember('cto', CometChat.GROUP_MEMBER_SCOPE.PARTICIPANT),
            new CometChat.GroupMember('ai_assistant', CometChat.GROUP_MEMBER_SCOPE.PARTICIPANT)
          ];
          await CometChat.addMembersToGroup(guid, membersList, []);
          return guid;
        } catch (createError) {
          console.error("Failed to create group", createError);
          return null;
        }
      }
      return guid;
    }
  },
  
  sendBotResponse: async (guid: string, query: string, candidateName: string) => {
    // Quick mock function to act like the AI responding
    try {
      // We must logout current user, login as AI, send, then log back as recruiter.
      // In a real app this is done via server-side webhook, but for frontend hackathon demo:
      const currentUser = await CometChat.getLoggedinUser();
      if (!currentUser) return;
      
      await CometChat.login('ai_assistant', AUTH_KEY);
      
      let responseText = `I analyzed the query about ${candidateName}. `;
      if (query.toLowerCase().includes('risk')) {
        responseText += "The main risk is timeline consistency and missing production experience in scalable architecture.";
      } else if (query.toLowerCase().includes('gem')) {
        responseText += "Their ATS score is low because they lack buzzwords, but they have deep expertise in building vector search engines!";
      } else if (query.toLowerCase().includes('interview')) {
        responseText += "I suggest asking: 'Can you describe a time you had to optimize a vector search index for latency?'";
      } else {
        responseText += "They rank highly due to strong semantic fit, but ensure you verify their latest project role.";
      }

      const textMessage = new CometChat.TextMessage(guid, responseText, CometChat.RECEIVER_TYPE.GROUP);
      await CometChat.sendMessage(textMessage);
      
      // Log back in as original user
      await CometChat.login(currentUser.getUid(), AUTH_KEY);
    } catch (err) {
      console.error("Bot failed to respond", err);
    }
  }
};
