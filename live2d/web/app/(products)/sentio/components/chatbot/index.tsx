'use client'

import { useState, memo } from 'react';
import { APP_TYPE, IFER_TYPE } from '@/lib/protocol';
import { ChatRecord } from './record';
import { DoubaoInputBar } from './doubaoBar';
import {
    useSentioThemeStore,
    useSentioAsrStore
} from '@/lib/store/sentio';

function FreedomChatBot() {
    const { infer_type } = useSentioAsrStore();
    const [voiceMode, setVoiceMode] = useState(false);

    return (
        <div className="flex flex-col full-height-minus-64px pb-6 md:px-6 gap-6 justify-between items-center z-10">
            <ChatRecord />
            {/* 豆包风格统一输入栏 */}
            <DoubaoInputBar
                voiceMode={voiceMode}
                onToggleMode={() => setVoiceMode(!voiceMode)}
                streamMode={infer_type == IFER_TYPE.STREAM}
            />
        </div>
    )
}

function ChatBot() {
    const { theme } = useSentioThemeStore();
    switch (theme) {
        case APP_TYPE.FREEDOM:
            return <FreedomChatBot />
        default:
            return <FreedomChatBot />
    }
}

export default memo(ChatBot);
