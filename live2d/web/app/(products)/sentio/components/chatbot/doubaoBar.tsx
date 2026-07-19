'use client'

import { useState, useRef, useEffect, useCallback, memo } from 'react';
import { MicrophoneIcon, PaperAirplaneIcon, PencilSquareIcon } from '@heroicons/react/24/solid';
import { useSentioAsrStore, useChatRecordStore } from '@/lib/store/sentio';
import { addToast } from '@heroui/react';
import { api_asr_infer_file } from '@/lib/api/server';
import { ChatStreamInput } from './input';
import { useChatWithAgent } from '../../hooks/chat';
import { convertFloat32ArrayToMp3 } from '@/lib/utils/audio';
import { useMicVAD } from '@ricky0123/vad-react';
import { getSrcPath } from '@/lib/path';
import clsx from 'clsx';

// ========================= 文字输入模式 =========================
const TextMode = memo(({
    onSend,
    chatting,
    onAbort
}: {
    onSend: (text: string) => void;
    chatting: boolean;
    onAbort: () => void;
}) => {
    const [message, setMessage] = useState('');

    const handleSend = () => {
        const text = message.trim();
        if (!text) return;
        setMessage('');
        onSend(text);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') handleSend();
    };

    return (
        <div className="flex items-center gap-2 w-full">
            <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息..."
                enterKeyHint="send"
                className="flex-1 px-4 py-2.5 rounded-full bg-white/60 backdrop-blur border border-gray-200
                           focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-300
                           text-sm placeholder:text-gray-400"
            />
            {chatting ? (
                <button
                    onClick={onAbort}
                    className="flex-shrink-0 w-10 h-10 rounded-full bg-red-500 text-white
                               flex items-center justify-center shadow hover:bg-red-600 transition"
                >
                    <div className="w-3 h-3 bg-white rounded-sm" />
                </button>
            ) : (
                <button
                    onClick={handleSend}
                    disabled={!message.trim()}
                    className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-500 text-white
                               flex items-center justify-center shadow hover:bg-amber-600 transition
                               disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    <PaperAirplaneIcon className="size-4 rotate-90 -translate-x-px" />
                </button>
            )}
        </div>
    );
});

// ========================= 语音输入模式 (VAD) =========================
const VoiceMode = memo(({
    onResult
}: {
    onResult: (text: string) => void;
}) => {
    const { engine: asrEngine, settings: asrSettings } = useSentioAsrStore();
    const [listening, setListening] = useState(false);
    const [speaking, setSpeaking] = useState(false);
    const [converting, setConverting] = useState(false);
    const waveRef = useRef<HTMLDivElement>(null);

    const handleSpeechEnd = useCallback(async (audio: Float32Array) => {
        setSpeaking(false);
        setConverting(true);
        try {
            const mp3Blob = convertFloat32ArrayToMp3(audio);
            const asrResult = await api_asr_infer_file(asrEngine, asrSettings, mp3Blob);
            if (asrResult.length > 0) {
                onResult(asrResult);
            }
        } catch (e: any) {
            addToast({ title: `语音识别失败: ${e.message}`, variant: 'flat', color: 'danger' });
        }
        setConverting(false);
    }, [asrEngine, asrSettings, onResult]);

    const vad = useMicVAD({
        baseAssetPath: getSrcPath('vad/'),
        onnxWASMBasePath: getSrcPath('vad/'),
        onSpeechStart: () => {
            setSpeaking(true);
        },
        onSpeechEnd: (audio) => {
            handleSpeechEnd(audio);
        },
        onVADMisfire: () => {
            setSpeaking(false);
        },
    });

    useEffect(() => {
        if (!vad.listening && !vad.loading) {
            vad.start();
        }
        setListening(vad.listening);
    }, [vad.listening, vad.loading]);

    let statusText = '正在聆听...';
    if (vad.loading) statusText = '加载语音模型...';
    else if (converting) statusText = '识别中...';
    else if (speaking) statusText = '正在识别...';
    else if (!listening) statusText = '等待麦克风...';

    return (
        <div className="flex items-center gap-3 w-full">
            {/* 波形指示器 */}
            <div
                ref={waveRef}
                className={clsx(
                    'flex-1 flex items-center justify-center gap-1 px-4 py-2.5 rounded-full transition-all',
                    speaking
                        ? 'bg-amber-100/80 border border-amber-300'
                        : 'bg-white/60 backdrop-blur border border-gray-200'
                )}
            >
                {/* 简易波形条 */}
                <div className="flex items-center gap-0.5 h-6">
                    {[1, 2, 3, 4, 3, 2, 1, 2, 3, 4, 3, 2].map((h, i) => (
                        <div
                            key={i}
                            className={clsx(
                                'w-0.5 rounded-full transition-all duration-200',
                                speaking ? 'bg-amber-500 animate-pulse' : 'bg-gray-300'
                            )}
                            style={{
                                height: speaking ? `${8 + h * 4}px` : `${4 + h * 1.5}px`,
                                animationDelay: `${i * 0.08}s`,
                            }}
                        />
                    ))}
                </div>
                <span className={clsx(
                    'ml-3 text-sm',
                    speaking ? 'text-amber-700 font-medium' : 'text-gray-400'
                )}>
                    {statusText}
                </span>
            </div>
        </div>
    );
});

// ========================= 豆包风格输入栏 =========================
export const DoubaoInputBar = memo(({
    voiceMode,
    onToggleMode,
    streamMode
}: {
    voiceMode: boolean;
    onToggleMode: () => void;
    streamMode: boolean;
}) => {
    const { chat, abort, chatting } = useChatWithAgent();
    const pendingExternalMessage = useChatRecordStore(s => s.pendingExternalMessage);
    const setPendingExternalMessage = useChatRecordStore(s => s.setPendingExternalMessage);

    // 监听外部消息
    useEffect(() => {
        if (pendingExternalMessage) {
            setPendingExternalMessage(null);
            chat(pendingExternalMessage);
        }
    }, [pendingExternalMessage]);

    const handleTextSend = useCallback((text: string) => {
        chat(text);
    }, [chat]);

    const handleVoiceResult = useCallback((text: string) => {
        chat(text);
    }, [chat]);

    // 语音模式切过来时打断 AI
    const handleToggle = useCallback(() => {
        if (!voiceMode) {
            abort(); // 切到语音时打断正在播放的 TTS
        }
        onToggleMode();
    }, [voiceMode, onToggleMode, abort]);

    // 如果是流式模式，嵌入 ChatStreamInput（WebSocket 流式 ASR）+ 切换按钮
    if (streamMode && voiceMode) {
        return (
            <div className="w-full max-w-lg">
                <div className="flex items-end gap-2">
                    <div className="flex-1">
                        <ChatStreamInput />
                    </div>
                    <button
                        onClick={handleToggle}
                        className="flex-shrink-0 w-10 h-10 mb-1 rounded-full bg-white/80 backdrop-blur
                                   flex items-center justify-center shadow hover:bg-white transition"
                    >
                        <PencilSquareIcon className="size-5 text-gray-500" />
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="w-full max-w-lg">
            <div className="flex items-center gap-2">
                {/* 左侧：模式切换按钮 */}
                <button
                    onClick={handleToggle}
                    className={clsx(
                        'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow transition',
                        voiceMode
                            ? 'bg-white/80 backdrop-blur hover:bg-white'
                            : 'bg-amber-50 hover:bg-amber-100'
                    )}
                    title={voiceMode ? '切换到文字输入' : '切换到语音输入'}
                >
                    {voiceMode ? (
                        <PencilSquareIcon className="size-5 text-gray-500" />
                    ) : (
                        <MicrophoneIcon className="size-5 text-amber-600" />
                    )}
                </button>

                {/* 中间：输入区域 */}
                {voiceMode ? (
                    <VoiceMode onResult={handleVoiceResult} />
                ) : (
                    <TextMode onSend={handleTextSend} chatting={chatting} onAbort={abort} />
                )}
            </div>
        </div>
    );
});
