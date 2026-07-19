'use client'

import { useEffect, useState, useCallback } from "react";
import { Live2d } from './components/live2d';
import ChatBot from './components/chatbot';
import { Header } from './components/header';
import { useAppConfig } from "./hooks/appConfig";
import { Spinner } from "@heroui/react";
import { useChatRecordStore, useSentioTtsStore } from "@/lib/store/sentio";
import { CHAT_ROLE } from "@/lib/protocol";
import { useChatWithAgent } from './hooks/chat';


export default function App() {
    const { setAppConfig } = useAppConfig();
    const [ isLoading, setIsLoading ] = useState(true);
    const { chat } = useChatWithAgent();

    // 初始化应用
    useEffect(() => {
        setAppConfig(null);
        setIsLoading(false);
    }, [])

    // 监听父窗口 (TourAI) 通过 postMessage 发送的消息
    useEffect(() => {
        const handler = (event: MessageEvent) => {
            const data = event.data;
            if (data && data.type === 'chat' && data.text) {
                // 直接调用 chat 触发 Agent + TTS + 嘴型动画
                chat(data.text);
            }
            if (data && data.type === 'config') {
                if (data.voice) {
                    const ttsStore = useSentioTtsStore.getState();
                    ttsStore.setSettings({ ...ttsStore.settings, voice: data.voice });
                }
            }
        };
        window.addEventListener('message', handler);
        return () => window.removeEventListener('message', handler);
    }, [chat])

    return (
        <div className='w-full h-full'>
            {
                isLoading ?
                <Spinner className="w-screen h-screen z-10" color="secondary" size="lg" variant="wave" />
                :
                <div className='flex flex-col w-full h-full'>
                    <Header />
                    <ChatBot />
                </div>
            }
            <Live2d />
        </div>
    );
}