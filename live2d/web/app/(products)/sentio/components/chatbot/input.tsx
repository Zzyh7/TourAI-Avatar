'use client'

import { useEffect, useState, memo, useRef } from 'react';
import { StopCircleIcon, MicrophoneIcon, PaperAirplaneIcon } from '@heroicons/react/24/solid';
import { useSentioAsrStore, useChatRecordStore } from '@/lib/store/sentio';
import { Input, Button, Spinner, addToast, Tooltip } from '@heroui/react';
import { CHAT_ROLE } from '@/lib/protocol';
import { api_asr_infer_file } from '@/lib/api/server';
import { createASRWebsocketClient, WS_RECV_ACTION_TYPE, WS_SEND_ACTION_TYPE } from '@/lib/api/websocket';
import { useTranslations } from 'next-intl';
import { convertToMp3, convertFloat32ArrayToMp3, AudioRecoder } from '@/lib/utils/audio';
import Recorder from 'js-audio-recorder';
import { useMicVAD } from "@ricky0123/vad-react"
import { useChatWithAgent, useAudioTimer } from '../../hooks/chat';
import { getSrcPath } from '@/lib/path';
import clsx from 'clsx';
import { Live2dManager } from '@/lib/live2d/live2dManager';

let micRecoder: Recorder | null = null;

// 每隔500ms检查一次Live2D状态
function startDebugMonitor() {
  const el = document.getElementById('lip-debug');
  if (!el) return;
  setInterval(() => {
    const lm = Live2dManager.getInstance();
    const audioPlaying = lm.isAudioPlaying();
    const lipFactor = lm.getLipFactor();
    const queueLen = (lm as any)._ttsQueue?.length || 0;
    const rms = lm.getLastRms();
    el.innerHTML = `🔊播放:${audioPlaying} 👄系数:${lipFactor} 📋队列:${queueLen} 🔊RMS:${rms.toFixed(4)}`;
    el.style.color = audioPlaying && rms > 0.001 ? '#0f0' : '#f00';
  }, 500);
}

export const ChatInput = memo(({
    postProcess
}: {
    postProcess?: (conversation_id: string, message_id: string, think: string, content: string) => void

}) => {
    const t = useTranslations('Products.sentio');
    const [message, setMessage] = useState("");
    const [startMicRecord, setStartMicRecord] = useState(false);
    const [startAsrConvert, setStartAsrConvert] = useState(false);
    const { enable: enableASR, engine: asrEngine, settings: asrSettings } = useSentioAsrStore();
    const { chat, abort, chatting } = useChatWithAgent();
    const { startAudioTimer, stopAudioTimer } = useAudioTimer();
    const pendingExternalMessage = useChatRecordStore(s => s.pendingExternalMessage);
    const setPendingExternalMessage = useChatRecordStore(s => s.setPendingExternalMessage);

    // 启动调试监视器
    useEffect(() => { startDebugMonitor(); }, []);

    // 监听父窗口 postMessage 触发的外部消息
    useEffect(() => {
        if (pendingExternalMessage) {
            setPendingExternalMessage(null);
            chat(pendingExternalMessage, postProcess);
        }
    }, [pendingExternalMessage]);

    const handleStartRecord = () => {
        abort();
        if (micRecoder == null) {
            micRecoder = new Recorder({
                sampleBits: 16,
                sampleRate: 16000,
                numChannels: 1,
                compiling: false,
            })
        }
        micRecoder.start().then(
            () => {
                startAudioTimer();
                setStartMicRecord(true);
            }, () => {
                addToast({
                    title: t('micOpenError'),
                    variant: "flat",
                    color: "danger"
                })
            }
        )
    }

    const handleStopRecord = async () => {
        micRecoder.stop();
        setStartMicRecord(false);
        if (!stopAudioTimer()) return;
        setMessage(t('speech2text'));
        setStartAsrConvert(true);
        const mp3Blob = convertToMp3(micRecoder);
        let asrResult = "";
        asrResult = await api_asr_infer_file(asrEngine, asrSettings, mp3Blob);
        if (asrResult.length > 0) {
            setMessage(asrResult);
        } else {
            setMessage("");
        }
        setStartAsrConvert(false);
    }

    const onFileClick = () => {
    }
    const onSendClick = () => {
        if (message == "") return;
        chat(message, postProcess);
        setMessage("");
    }
    const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
            onSendClick();
        }
    }
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "m" && e.ctrlKey) {
                if (startMicRecord) {
                    handleStopRecord();
                } else {
                    handleStartRecord();
                }
            }
        }
        window.addEventListener("keydown", handleKeyDown);
        return () => {
            window.removeEventListener("keydown", handleKeyDown);
        }
    })

    return (
        <div className='flex flex-col w-4/5 md:w-2/3 2xl:w-1/2 items-start z-10 gap-2'>
            {/* 调试指示器 */}
            <div id="lip-debug" style={{
              position:'fixed',top:0,left:0,zIndex:9999,
              background:'rgba(0,0,0,0.8)',color:'#0f0',
              padding:'4px 12px',fontSize:12,fontFamily:'monospace',
              borderRadius:'0 0 8px 0'
            }}>等待音频...</div>
            <div className='flex w-full items-center z-10'>
                <Input
                    className='opacity-90'
                    startContent={
                        <button
                            type="button"
                            disabled={!enableASR}
                            aria-label="toggle password visibility"
                            className={clsx(
                                "focus:outline-none",
                                startMicRecord ? "text-red-500" : enableASR ? "hover:text-green-500" : "hover:text-gray-500"
                            )}
                        >
                            {startMicRecord ? (
                                <StopCircleIcon className='size-6' onClick={handleStopRecord} />
                            ) : (
                                startAsrConvert ? (
                                    <Spinner size="sm" />
                                ) : (
                                    <Tooltip className='opacity-90' content="Ctrl + M">
                                        <MicrophoneIcon className='size-6' onClick={handleStartRecord} />
                                    </Tooltip>
                                )
                            )}
                        </button>
                    }
                    endContent={
                        chatting ?
                            <button
                                type="button"
                                onClick={abort}
                                className="focus:outline-none hover:text-red-500"
                            >
                                <StopCircleIcon className='size-6' />
                            </button>
                            :
                            <></>
                    }
                    type='text'
                    enterKeyHint='send'
                    value={message}
                    onValueChange={setMessage}
                    onKeyDown={onKeyDown}
                    disabled={startMicRecord || startAsrConvert}
                />
                <Button className='opacity-90' isIconOnly color="primary" onPress={onSendClick}>
                    <PaperAirplaneIcon className='size-6' />
                </Button>
            </div>
        </div>
    )
});

const convertFloat32ToAnalyseData = (float32Data: Float32Array) => {
    const analyseData = new Uint8Array(float32Data.length);
    const dataLength = float32Data.length;

    for (let i = 0; i < dataLength; i++) {
        const value = float32Data[i];
        const mappedValue = Math.round((value + 1) * 128);
        analyseData[i] = Math.max(0, Math.min(255, mappedValue));
    }

    return analyseData;
}

export const ChatVadInput = memo(() => {
    const t = useTranslations('Products.sentio');
    const canvasRef = useRef<HTMLCanvasElement | null>(null)
    const ctxRef = useRef<CanvasRenderingContext2D | null>(null)
    const { engine: asrEngine, settings: asrSettings } = useSentioAsrStore();
    const { chat, abort } = useChatWithAgent();
    const { startAudioTimer, stopAudioTimer } = useAudioTimer();
    const waveData = useRef<Uint8Array | null>();
    const drawId = useRef<number | null>(null);

    const handleSpeechEnd = async (audio: Float32Array) => {
        const mp3Blob = convertFloat32ArrayToMp3(audio);
        let asrResult = ""
        asrResult = await api_asr_infer_file(asrEngine, asrSettings, mp3Blob);
        if (asrResult.length > 0) {
            chat(asrResult);
        }
    }
    const vad = useMicVAD({
        baseAssetPath: getSrcPath("vad/"),
        onnxWASMBasePath: getSrcPath("vad/"),
        onSpeechStart: () => {
            abort();
            startAudioTimer();
        },
        onFrameProcessed: (audio, frame) => {
            const dataUnit8Array = convertFloat32ToAnalyseData(frame);
            waveData.current = dataUnit8Array;
        },
        onSpeechEnd: (audio) => {
            if (stopAudioTimer()) {
                handleSpeechEnd(audio);
            }
        },
    });

    const initCanvas = () => {
        const dpr = window.devicePixelRatio || 1
        const canvas = document.getElementById('voice-input') as HTMLCanvasElement

        if (canvas) {
            const { width: cssWidth, height: cssHeight } = canvas.getBoundingClientRect()

            canvas.width = dpr * cssWidth
            canvas.height = dpr * cssHeight
            canvasRef.current = canvas

            const ctx = canvas.getContext('2d')
            if (ctx) {
                ctx.scale(dpr, dpr)
                ctx.fillStyle = 'rgb(215, 183, 237)'
                ctxRef.current = ctx
            }
        }
    }

    function drawCanvas() {
        const canvas = canvasRef.current!
        const ctx = ctxRef.current!
        if (canvas && ctx && waveData.current) {
            const resolution = 3
            const dataArray = [].slice.call(waveData.current)
            const lineLength = parseInt(`${canvas.width / resolution}`)
            const gap = parseInt(`${dataArray.length / lineLength}`)

            ctx.clearRect(0, 0, canvas.width, canvas.height)
            ctx.beginPath()
            let x = 0
            for (let i = 0; i < lineLength; i++) {
                let v = dataArray.slice(i * gap, i * gap + gap).reduce((prev: number, next: number) => {
                    return prev + next
                }, 0) / gap

                const y = (v - 128) / 128 * canvas.height

                ctx.moveTo(x, 16)
                if (ctx.roundRect)
                    ctx.roundRect(x, 16 - y, 2, y, [1, 1, 0, 0])
                else
                    ctx.rect(x, 16 - y, 2, y)
                ctx.fill()
                x += resolution
            }
            ctx.closePath();
        }
        drawId.current = requestAnimationFrame(drawCanvas);
    }

    useEffect(() => {
        initCanvas();
        drawId.current = requestAnimationFrame(drawCanvas);
        return () => {
            !!drawId.current && cancelAnimationFrame(drawId.current);
        }
    }, [])

    return (
        <div className='flex flex-col h-10 w-1/2 md:w-1/3 items-center'>
            {vad.loading && <div className='flex flex-row gap-1 items-center'>
                    <p className='text-xl font-bold'>{t('loading')}</p>
                    <Spinner color='warning' variant="dots" size='lg'/>
                </div>
            }
            <canvas id="voice-input" className='h-full w-full' />
        </div>

    )
});

export const ChatStreamInput = memo(() => {
    const t = useTranslations('Products.sentio');
    const canvasRef = useRef<HTMLCanvasElement | null>(null)
    const ctxRef = useRef<CanvasRenderingContext2D | null>(null)
    const { chat, abort } = useChatWithAgent();
    const { engine, settings } = useSentioAsrStore();
    const { getLastRecord, updateLastRecord, addChatRecord, deleteLastRecord } = useChatRecordStore();
    const waveData = useRef<Uint8Array | null>();
    const drawId = useRef<number | null>(null);
    const [engineLoading, setEngineLoading] = useState<boolean>(true);
    const engineReady = useRef<boolean>(false);

    const initCanvas = () => {
        const dpr = window.devicePixelRatio || 1
        const canvas = document.getElementById('voice-input') as HTMLCanvasElement

        if (canvas) {
            const { width: cssWidth, height: cssHeight } = canvas.getBoundingClientRect()

            canvas.width = dpr * cssWidth
            canvas.height = dpr * cssHeight
            canvasRef.current = canvas

            const ctx = canvas.getContext('2d')
            if (ctx) {
                ctx.scale(dpr, dpr)
                ctx.fillStyle = 'rgb(215, 183, 237)'
                ctxRef.current = ctx
            }
        }
    }

    function drawCanvas() {
        const canvas = canvasRef.current!
        const ctx = ctxRef.current!
        if (canvas && ctx && waveData.current) {
            const dataArray = [].slice.call(waveData.current)
            const resolution = 10
            const lineLength = parseInt(`${canvas.width / resolution}`)
            const gap = parseInt(`${dataArray.length / lineLength}`)
            ctx.clearRect(0, 0, canvas.width, canvas.height)
            ctx.beginPath()
            let x = 0
            for (let i = 0; i < lineLength; i++) {
                let v = dataArray.slice(i * gap, i * gap + gap).reduce((prev: number, next: number) => {
                    return prev + next
                }, 0) / gap

                const y = (v - 128) / 128 * canvas.height

                ctx.moveTo(x, 16)
                if (ctx.roundRect)
                    ctx.roundRect(x, 16 - y, 2, y, [1, 1, 0, 0])
                else
                    ctx.rect(x, 16 - y, 2, y)
                ctx.fill()
                x += resolution
            }
            ctx.closePath();
        }
        drawId.current = requestAnimationFrame(drawCanvas);
    }

    useEffect(() => {
        const asrWsClient = createASRWebsocketClient({
            engine: engine,
            config: settings,
            onMessage: (action: string, data: Uint8Array) => {
                const recvAction = action as WS_RECV_ACTION_TYPE;
                const recvData = new TextDecoder('utf-8').decode(data).trim();
                switch (recvAction) {
                    case WS_RECV_ACTION_TYPE.ENGINE_INITIALZING:
                        break;
                    case WS_RECV_ACTION_TYPE.ENGINE_STARTED:
                        setEngineLoading(false);
                        engineReady.current = true;
                        break;
                    case WS_RECV_ACTION_TYPE.ENGINE_PARTIAL_OUTPUT:
                        const lastChatRecord = getLastRecord();
                        if (lastChatRecord && lastChatRecord.role == CHAT_ROLE.AI) {
                            abort();
                            addChatRecord({ role: CHAT_ROLE.HUMAN, think: "", content: recvData })
                        } else {
                            updateLastRecord({ role: CHAT_ROLE.HUMAN, think: "", content: recvData })
                        }
                        break;
                    case WS_RECV_ACTION_TYPE.ENGINE_FINAL_OUTPUT:
                        deleteLastRecord();
                        chat(recvData);
                        break;
                    case WS_RECV_ACTION_TYPE.ENGINE_STOPPED:
                        setEngineLoading(true);
                        engineReady.current = false;
                        break;
                    case WS_RECV_ACTION_TYPE.ERROR:
                        setEngineLoading(true);
                        engineReady.current = false;
                        addToast({
                            title: recvData,
                            variant: "flat",
                            color: "danger"
                        })
                        break;
                    default:
                        break;
                }
            },
            onError: (error: Error) => {
                addToast({
                    title: error.message,
                    variant: "flat",
                    color: "danger"
                })
            }
        })
        const audioRecoder = new AudioRecoder(
            16000,
            1,
            16000 / 1000 * 60 * 2,
            (chunk: Uint8Array) => {
                try {
                    if (asrWsClient.isConnected && engineReady.current) {
                        asrWsClient.sendMessage(WS_SEND_ACTION_TYPE.ENGINE_PARTIAL_INPUT, chunk)
                    }
                } catch(error: any) {
                    addToast({
                        title: error.message,
                        variant: "flat",
                        color: "danger"
                    })
                }
            },
            (chunk: Float32Array) => {
                if (engineReady.current) {
                    waveData.current = convertFloat32ToAnalyseData(chunk);
                }
            }
        );
        initCanvas();
        drawId.current = requestAnimationFrame(drawCanvas);
        asrWsClient.connect();
        audioRecoder.start();

        return () => {
            audioRecoder.stop();
            asrWsClient.disconnect();
            !!drawId.current && cancelAnimationFrame(drawId.current);
        }
    }, [])

    return (
        <div className='flex flex-col h-10 w-1/2 md:w-1/3 items-center'>
            {engineLoading && <div className='flex flex-row gap-1 items-center'>
                    <p className='text-xl font-bold'>{t('loading')}</p>
                    <Spinner color='warning' variant="dots" size='lg'/>
                </div>
            }
            <canvas id="voice-input" className='h-full w-full' />
        </div>

    )
});