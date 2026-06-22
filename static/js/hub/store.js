import { createConversationId } from "./utils.js";

export const state = {
    conversationId: createConversationId(),
    conversations: [],
    messages: [],
    currentConversation: null,
    latestEvaluation: null,
    latestAdvisorContext: null,
    selectedEvaluationCriteria: [],
    socket: null,
    socketReady: false,
    pendingRequests: new Map(),
    loadingConversationId: "",
};
