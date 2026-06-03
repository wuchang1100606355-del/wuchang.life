import React, { useState, useEffect, useRef } from 'react';
import {
    Home, Wallet, User, Bell, Settings, CreditCard, Smartphone,
    Megaphone, Server, ShieldCheck, ChevronRight, RefreshCw,
    CheckCircle, AlertCircle, X, Plus, LogOut, QrCode, Building,
    MessageCircle, Link, Users, ExternalLink, Send, Image, Mic,
    MessageSquare, Pin, LayoutDashboard, FileSignature, Printer,
    DollarSign, Wrench, Crown, Bot, Sparkles, Database, FileSpreadsheet,
    PieChart, ArrowUpRight, ArrowDownLeft, ScanLine, Heart, MapPin,
    ShoppingBag, Star, Clock, Bike, TreeDeciduous, Sprout, Coins, Handshake,
    Map, Grid, Globe, Activity, Coffee, Award, Scale, BookOpen, GraduationCap,
    Truck, ClipboardList, Trash2, Minus, Flame, Smile, ThumbsUp, Zap, Droplets, Wifi, Store
} from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart as RePieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts';

// ==========================================
// 1. MOCK DATA
// ==========================================
const ROLES = {
    RESIDENT: { id: 'resident', name: '林志明 (3F-2)', roleName: '住戶', color: 'bg-green-600', access: 'portal' },
    ADMIN: { id: 'admin', name: '江政隆', roleName: '總幹事', color: 'bg-gray-800', access: 'full' },
};

const INITIAL_STATE = {
    user: {
        happinessCoins: 850,
        proposalGrant: 12000, // 非營利機構營運補助暨社區提案補助金
        managementFee: 3500,
        isFeePaid: false,
        barcode: '/AB1+234',
        isLinePayLinked: true
    },
    notices: [
        { id: 's1', title: '系統維護通知', date: '11/06', content: '系統將於明日凌晨進行升級。', type: 'system' },
        { id: 'c1', title: '【重要】消防安檢', date: '11/05', content: '請勿在梯間堆放雜物。', type: 'community' },
    ],
    fundTransactions: [
        { id: "tx1", date: "2023-10-01", type: "income", category: "商家提撥", amount: 15000, desc: "聊國咖啡-9月營收回饋" },
        { id: "tx2", date: "2023-10-05", type: "income", category: "資源回收", amount: 3200, desc: "變賣所得全額入帳" },
        { id: "tx3", date: "2023-10-10", type: "expense", category: "設施維護", amount: 8500, desc: "五常公園遊具修繕" }
    ]
};

// ==========================================
// 2. SUB-COMPONENTS
// ==========================================

// --- 4. 許願樹 (Wishing Tree) ---
const WishTab = ({ onBack, globalState }) => (
    <div className="flex flex-col h-full bg-slate-50" id="wishing-tree-page">
        <div className="bg-pink-600 text-white p-4 flex items-center shadow-lg">
            <button onClick={onBack} className="mr-4" id="btn-wish-back"><ChevronRight className="rotate-180" /></button>
            <h2 className="font-bold">社區許願樹</h2>
        </div>
        <div className="p-4 space-y-4">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-pink-100">
                <div className="flex justify-between items-start mb-4">
                    <h3 className="font-bold text-lg text-slate-800">增設頂樓空中花園</h3>
                    <span className="bg-pink-100 text-pink-600 text-xs px-2 py-1 rounded-full">募集中</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 mb-2">
                    <div className="bg-pink-500 h-2 rounded-full" style={{ width: '70%' }}></div>
                </div>
                <div className="flex justify-between text-xs text-slate-500 mb-4">
                    <span>已募得 35,000 點</span>
                    <span>目標 50,000 點</span>
                </div>

                <div className="bg-gray-50 p-3 rounded-lg mb-4 text-xs text-gray-600">
                    <p className="font-bold mb-1">您的補助金餘額: ${globalState.user.proposalGrant.toLocaleString()}</p>
                    <p>此款項僅可用於非營利機構營運或公眾利益提案。</p>
                </div>

                <button className="w-full py-3 bg-pink-600 text-white rounded-lg font-bold shadow hover:bg-pink-700 transition-colors">
                    使用「提案補助金」灌溉支持
                </button>
            </div>
        </div>
    </div>
);

// --- 2. 商家平台 (Market) ---
const MarketTab = ({ onBack }) => (
    <div className="flex flex-col h-full bg-slate-50" id="market-page">
        <div className="bg-white p-4 border-b flex items-center gap-3 sticky top-0 z-10">
            <button onClick={onBack} id="btn-market-back"><ArrowUpRight className="rotate-180" /></button>
            <h2 className="font-bold">公益商家聯合銷售</h2>
        </div>
        <div className="p-4">
            <div className="bg-indigo-50 p-4 rounded-xl mb-4 text-sm text-indigo-700 flex gap-3">
                <ShoppingBag className="flex-shrink-0" />
                <div>
                    <p className="font-bold">消費即公益</p>
                    <p className="text-xs mt-1">每一筆消費扣除成本後，100% 回歸社區基金。</p>
                </div>
            </div>
            {/* Mock Stores */}
            <div className="space-y-3">
                <div className="bg-white p-4 rounded-xl shadow-sm border flex gap-4">
                    <div className="w-20 h-20 bg-gray-200 rounded-lg bg-cover bg-center" style={{ backgroundImage: "url('/web/image/wuchang_os.img_shop_sign')" }}></div>
                    <div className="flex-1">
                        <h3 className="font-bold">上品聊國咖啡</h3>
                        <p className="text-xs text-gray-500">基金池直營店 • 咖啡/輕食</p>
                        <div className="mt-2 flex gap-2">
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">可外送</span>
                            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">接受幸福幣</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
);

// --- 3. 基金平台 (Fund) ---
const FundTab = ({ onBack, globalState }) => (
    <div className="flex flex-col h-full bg-slate-50">
        <div className="bg-emerald-600 text-white p-4 flex items-center shadow-lg">
            <button onClick={onBack} className="mr-4"><ChevronRight className="rotate-180" /></button>
            <h2 className="font-bold">發展基金運作看板</h2>
        </div>
        <div className="p-4 space-y-4">
            <div className="bg-white p-6 rounded-xl shadow-sm text-center">
                <p className="text-slate-500 text-sm">目前基金水位</p>
                <p className="text-3xl font-bold text-emerald-600">$35,820,000</p>
            </div>
            {globalState.fundTransactions.map(tx => (
                <div key={tx.id} id={`fund-tx-${tx.id}`} className="bg-white p-3 rounded-lg border border-slate-100 flex justify-between text-sm">
                    <span>{tx.desc}</span>
                    <span className={tx.type === 'income' ? 'text-emerald-600' : 'text-red-600'}>
                        {tx.type === 'income' ? '+' : '-'}${tx.amount}
                    </span>
                </div>
            ))}
        </div>
    </div>
);

// --- 5. 志工平台 (Volunteer) ---
const VolunteerTab = ({ onBack }) => (
    <div className="flex flex-col h-full bg-slate-50">
        <div className="bg-orange-500 text-white p-4 flex items-center shadow-lg">
            <button onClick={onBack} className="mr-4"><ChevronRight className="rotate-180" /></button>
            <h2 className="font-bold">志工隊管理及派遣</h2>
        </div>
        <div className="p-4 space-y-4">
            <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
                <h4 className="font-bold">愛心送餐 - 林奶奶</h4>
                <p className="text-xs text-slate-500 mt-1">五常里仁愛街 5 號</p>
                <div className="mt-3 flex justify-between items-center">
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">+50 幸福幣</span>
                    <button className="text-sm bg-slate-900 text-white px-3 py-1.5 rounded-lg">接單</button>
                </div>
            </div>
        </div>
    </div>
);

// --- 1. 系統最高權限主控台 (Supreme Command Console) ---
const SupremeCommandConsole = ({ onBack }) => {
    const [view, setView] = useState('dashboard'); // dashboard, ai_config
    const [aiConfig, setAiConfig] = useState({
        behavior: 'friendly',
        weights: { public: 0.9, efficiency: 0.5, community: 0.8, profit: 0.2 }
    });
    const [command, setCommand] = useState('');
    const [logs, setLogs] = useState([{ id: 1, text: '系統啟動完成', type: 'info' }]);

    const handleCommand = () => {
        if (!command.trim()) return;
        setLogs(prev => [...prev, { id: Date.now(), text: `> ${command}`, type: 'user' }]);
        setTimeout(() => {
            setLogs(prev => [...prev, { id: Date.now() + 1, text: `AI: 已接收指令，正在分析影響範圍...`, type: 'ai' }]);
        }, 500);
        setCommand('');
    };

    return (
        <div className="flex flex-col h-full bg-slate-900 text-white">
            <div className="p-4 flex items-center justify-between border-b border-slate-700">
                <div className="flex items-center gap-3">
                    <button onClick={onBack}><ArrowUpRight className="rotate-180" /></button>
                    <div>
                        <h2 className="font-bold flex items-center gap-2"><ShieldCheck className="text-red-500" /> 最高權限主控台</h2>
                        <span className="text-[10px] text-slate-400">Supreme Command Console</span>
                    </div>
                </div>
                <div className="flex bg-slate-800 rounded-lg p-1">
                    <button onClick={() => setView('dashboard')} className={`px-3 py-1 rounded ${view === 'dashboard' ? 'bg-slate-600 text-white' : 'text-slate-400'}`}>戰情看板</button>
                    <button onClick={() => setView('ai_config')} className={`px-3 py-1 rounded ${view === 'ai_config' ? 'bg-slate-600 text-white' : 'text-slate-400'}`}>AI 總路由</button>
                </div>
            </div>

            <div className="flex-1 overflow-auto p-4">
                {view === 'dashboard' && (
                    <div className="text-center text-slate-400 mt-10">
                        <Globe size={48} className="mx-auto mb-4 opacity-50" />
                        <p>全域監控地圖載入中...</p>
                    </div>
                )}

                {view === 'ai_config' && (
                    <div className="max-w-2xl mx-auto space-y-6">
                        {/* 1. Behavior Mode */}
                        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
                            <h3 className="font-bold mb-3 text-emerald-400">AI 行為模式 (Behavior Mode)</h3>
                            <div className="grid grid-cols-3 gap-3">
                                {['strict', 'friendly', 'efficient'].map(mode => (
                                    <button
                                        key={mode}
                                        onClick={() => setAiConfig({ ...aiConfig, behavior: mode })}
                                        className={`p-3 rounded-lg border ${aiConfig.behavior === mode ? 'border-emerald-500 bg-emerald-500/20 text-white' : 'border-slate-600 text-slate-400'}`}
                                    >
                                        {mode === 'strict' && '嚴肅合規'}
                                        {mode === 'friendly' && '溫暖親切'}
                                        {mode === 'efficient' && '效率優先'}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* 2. Value Weights */}
                        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700">
                            <h3 className="font-bold mb-4 text-emerald-400">價值觀權重 (Value Weights)</h3>
                            <div className="space-y-4">
                                <div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span>公益性 (Public Interest)</span>
                                        <span className="text-emerald-400">{aiConfig.weights.public}</span>
                                    </div>
                                    <input type="range" min="0" max="1" step="0.1" value={aiConfig.weights.public} onChange={e => setAiConfig({ ...aiConfig, weights: { ...aiConfig.weights, public: parseFloat(e.target.value) } })} className="w-full accent-emerald-500" />
                                </div>
                                <div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span>商業利益 (Commercial Profit)</span>
                                        <span className="text-red-400">{aiConfig.weights.profit}</span>
                                    </div>
                                    <input type="range" min="0" max="1" step="0.1" value={aiConfig.weights.profit} onChange={e => setAiConfig({ ...aiConfig, weights: { ...aiConfig.weights, profit: parseFloat(e.target.value) } })} className="w-full accent-red-500" />
                                    <p className="text-[10px] text-slate-500 mt-1">* 商業利益權重不可高於公益性</p>
                                </div>
                            </div>
                        </div>

                        {/* 3. Command Interface */}
                        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 flex flex-col h-64">
                            <h3 className="font-bold mb-2 text-emerald-400">系統調度指令 (System Dispatch)</h3>
                            <div className="flex-1 bg-black/30 rounded-lg p-3 overflow-y-auto mb-3 font-mono text-sm space-y-1">
                                {logs.map(log => (
                                    <div key={log.id} className={log.type === 'user' ? 'text-white' : 'text-emerald-500'}>{log.text}</div>
                                ))}
                            </div>
                            <div className="flex gap-2">
                                <input
                                    className="flex-1 bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm outline-none focus:border-emerald-500"
                                    placeholder="輸入自然語言指令..."
                                    value={command}
                                    onChange={e => setCommand(e.target.value)}
                                    onKeyPress={e => e.key === 'Enter' && handleCommand()}
                                />
                                <button onClick={handleCommand} className="bg-emerald-600 px-4 py-2 rounded text-sm font-bold hover:bg-emerald-700">執行</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

// ==========================================
// 3. RESIDENT PORTAL (Main User Interface)
// ==========================================
const ResidentPortal = ({ currentRole, globalState, setGlobalState, onNavigate }) => {
    const [tab, setTab] = useState('home'); // home, wallet, chat, profile

    return (
        <div className="flex justify-center bg-gray-200 h-screen font-sans">
            <div className="w-full max-w-md bg-gray-50 h-full flex flex-col relative overflow-hidden shadow-2xl">

                {/* 1. HOME TAB */}
                <div className="flex-1 overflow-y-auto pb-24 scroll-smooth">
                    {/* Header with Glassmorphism */}
                    <div className="bg-slate-900/90 backdrop-blur-md text-white p-6 rounded-b-[2.5rem] shadow-2xl mb-6 relative overflow-hidden border-b border-white/10">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/20 rounded-full blur-3xl -mr-16 -mt-16 animate-pulse"></div>
                        <div className="relative z-10">
                            <div className="flex justify-between items-center mb-4">
                                <div>
                                    <p className="text-xs text-gray-400">早安，{ROLES[currentRole].name.split(' ')[0]}</p>
                                    <h1 className="text-xl font-bold flex items-center">
                                        五常智慧社區雲
                                    </h1>
                                </div>
                                <div className="bg-white/10 p-2 rounded-full relative"><Bell className="w-5 h-5" /><span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></span></div>
                            </div>
                            <div className="bg-white/10 backdrop-blur rounded-xl p-4 flex justify-between items-center border border-white/20">
                                <div>
                                    <p className="text-xs text-gray-300">本期管理費</p>
                                    <div className="flex items-center mt-1">
                                        <span className="text-xl font-bold mr-2">${globalState.user.managementFee.toLocaleString()}</span>
                                        <span className={`text-xs px-2 py-0.5 rounded ${globalState.user.isFeePaid ? 'bg-green-500' : 'bg-red-500'}`}>
                                            {globalState.user.isFeePaid ? '已繳' : '未繳'}
                                        </span>
                                    </div>
                                </div>
                                {!globalState.user.isFeePaid && (
                                    <button onClick={() => setTab('wallet')} className="bg-yellow-400 text-gray-900 px-3 py-1.5 rounded text-xs font-bold">前往繳費</button>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="px-4 mb-6 grid grid-cols-2 gap-3" id="main-shortcuts">
                        <button onClick={() => onNavigate('volunteer')} id="nav-btn-volunteer" className="bg-orange-50 p-4 rounded-xl flex items-center gap-3 shadow-sm border border-orange-100">
                            <div className="bg-orange-100 p-2 rounded-full text-orange-600"><Truck className="w-5 h-5" /></div>
                            <span className="font-bold text-gray-700">志工專區</span>
                        </button>
                        <button onClick={() => onNavigate('wishing')} id="nav-btn-wishing" className="bg-pink-50 p-4 rounded-xl flex items-center gap-3 shadow-sm border border-pink-100">
                            <div className="bg-pink-100 p-2 rounded-full text-pink-600"><Sprout className="w-5 h-5" /></div>
                            <span className="font-bold text-gray-700">許願樹</span>
                        </button>
                        <button onClick={() => onNavigate('market')} id="nav-btn-market" className="bg-indigo-50 p-4 rounded-xl flex items-center gap-3 shadow-sm border border-indigo-100">
                            <div className="bg-indigo-100 p-2 rounded-full text-indigo-600"><ShoppingBag className="w-5 h-5" /></div>
                            <span className="font-bold text-gray-700">公益市集</span>
                        </button>
                        <button onClick={() => onNavigate('fund')} id="nav-btn-fund" className="bg-emerald-50 p-4 rounded-xl flex items-center gap-3 shadow-sm border border-emerald-100">
                            <div className="bg-emerald-100 p-2 rounded-full text-emerald-600"><PieChart className="w-5 h-5" /></div>
                            <span className="font-bold text-gray-700">基金看板</span>
                        </button>
                    </div>

                    {/* Notices */}
                    <div className="px-4 space-y-3">
                        <h2 className="font-bold text-gray-700">最新公告</h2>
                        {globalState.notices.map(n => (
                            <div key={n.id} className={`p-4 rounded-xl border shadow-sm ${n.type === 'system' ? 'bg-blue-50 border-blue-100' : 'bg-white border-gray-100'}`}>
                                <div className="flex items-center mb-1">
                                    <span className={`text-[10px] px-2 rounded mr-2 text-white ${n.type === 'system' ? 'bg-blue-500' : 'bg-orange-500'}`}>{n.type === 'system' ? '系統' : '社區'}</span>
                                    <span className="text-xs text-gray-400">{n.date}</span>
                                </div>
                                <h3 className="font-bold text-sm text-gray-800">{n.title}</h3>
                                <p className="text-xs text-gray-600 mt-1">{n.content}</p>
                            </div>
                        ))}
                    </div>
                </div>
                )}

                {/* 2. WALLET TAB (Corrected) */}
                {tab === 'wallet' && (
                    <div className="flex-1 overflow-y-auto pb-24">
                        <div className="bg-[#06C755] text-white p-6 rounded-b-[2rem] shadow-lg mb-6">
                            <h1 className="font-bold text-xl mb-6">我的錢包</h1>
                            <div className="flex justify-between items-end">
                                <div>
                                    <p className="text-sm opacity-80">幸福幣餘額</p>
                                    <p className="text-3xl font-bold">{globalState.user.happinessCoins.toLocaleString()}</p>
                                </div>
                                <QrCode className="w-8 h-8 opacity-80" />
                            </div>
                        </div>

                        <div className="px-4 -mt-12 mb-6 relative z-10">
                            <div className="bg-white rounded-xl shadow p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-gray-400 font-bold">支付連結狀態</span>
                                    <span className={`text-xs px-2 py-0.5 rounded-full ${globalState.user.isLinePayLinked ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
                                        {globalState.user.isLinePayLinked ? '已連結' : '未連結'}
                                    </span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-8 h-8 bg-green-500 rounded flex items-center justify-center text-white font-bold text-xs">L</div>
                                    <span className="text-sm font-bold">LINE Pay</span>
                                </div>
                                <p className="text-[10px] text-gray-400 mt-2 text-center border-t pt-2">
                                    * 協會不代收儲值金，此處僅顯示第三方支付連結狀態
                                </p>
                            </div>
                        </div>

                        <div className="px-4 space-y-4">
                            <h3 className="font-bold text-gray-700">生活繳費</h3>

                            {/* Management Fee */}
                            <button className="w-full bg-white border border-red-200 p-4 rounded-xl shadow-sm flex justify-between items-center">
                                <div className="flex items-center">
                                    <div className="bg-red-100 p-2 rounded-lg mr-3"><Building className="w-5 h-5 text-red-500" /></div>
                                    <div className="text-left">
                                        <p className="font-bold text-gray-800">管理費</p>
                                        <p className="text-xs text-gray-500">${globalState.user.managementFee}</p>
                                    </div>
                                </div>
                                <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded">幸福幣折抵</span>
                            </button>

                            {/* Utility Bills */}
                            <div className="grid grid-cols-3 gap-3">
                                <button className="bg-white p-3 rounded-xl border border-gray-100 flex flex-col items-center gap-2 hover:bg-blue-50">
                                    <Droplets className="text-blue-500 w-6 h-6" />
                                    <span className="text-xs font-bold text-gray-600">水費</span>
                                </button>
                                <button className="bg-white p-3 rounded-xl border border-gray-100 flex flex-col items-center gap-2 hover:bg-yellow-50">
                                    <Zap className="text-yellow-500 w-6 h-6" />
                                    <span className="text-xs font-bold text-gray-600">電費</span>
                                </button>
                                <button className="bg-white p-3 rounded-xl border border-gray-100 flex flex-col items-center gap-2 hover:bg-purple-50">
                                    <Wifi className="text-purple-500 w-6 h-6" />
                                    <span className="text-xs font-bold text-gray-600">電信費</span>
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                <div className="bg-white border-t h-20 flex justify-around items-start pt-3 absolute bottom-0 w-full z-20" id="bottom-nav">
                    <button onClick={() => setTab('home')} id="tab-home" className={`flex flex-col items-center w-16 ${tab === 'home' ? 'text-blue-600' : 'text-gray-400'}`}><Home className="w-6 h-6" /><span className="text-[10px] mt-1">首頁</span></button>
                    <button onClick={() => onNavigate('market')} id="tab-market" className={`flex flex-col items-center w-16 text-gray-400`}><Store className="w-6 h-6" /><span className="text-[10px] mt-1">市集</span></button>
                    <button onClick={() => alert('開發中')} id="tab-chat" className={`flex flex-col items-center w-16 text-gray-400`}><MessageCircle className="w-6 h-6" /><span className="text-[10px] mt-1">聊天</span></button>
                    <button onClick={() => setTab('wallet')} id="tab-wallet" className={`flex flex-col items-center w-16 ${tab === 'wallet' ? 'text-blue-600' : 'text-gray-400'}`}><Wallet className="w-6 h-6" /><span className="text-[10px] mt-1">錢包</span></button>
                    <button onClick={() => alert('開發中')} id="tab-profile" className={`flex flex-col items-center w-16 text-gray-400`}><User className="w-6 h-6" /><span className="text-[10px] mt-1">我的</span></button>
                </div>
            </div>
        </div>
    );
};

// ==========================================
// 4. ROOT COMPONENT
// ==========================================
export default function CommunitySuperApp() {
    const [currentRole, setCurrentRole] = useState('RESIDENT');
    const [systemMode, setSystemMode] = useState('portal'); // portal, erp, volunteer, wishing, market, fund
    const [globalState, setGlobalState] = useState(INITIAL_STATE);

    // AI Helper State
    const [showAi, setShowAi] = useState(false);

    return (
        <div className="relative">
            {/* View Router */}
            {systemMode === 'portal' && (
                <ResidentPortal
                    currentRole={currentRole}
                    globalState={globalState}
                    setGlobalState={setGlobalState}
                    onNavigate={setSystemMode}
                />
            )}

            {systemMode === 'erp' && (
                <ManagementERP onBack={() => setSystemMode('portal')} />
            )}

            {systemMode === 'volunteer' && (
                <VolunteerTab onBack={() => setSystemMode('portal')} />
            )}

            {systemMode === 'wishing' && (
                <WishTab onBack={() => setSystemMode('portal')} globalState={globalState} />
            )}

            {systemMode === 'market' && (
                <MarketTab onBack={() => setSystemMode('portal')} />
            )}

            {systemMode === 'fund' && (
                <FundTab onBack={() => setSystemMode('portal')} globalState={globalState} />
            )}

            {/* Global AI Floating Button */}
            <button
                onClick={() => setShowAi(!showAi)}
                className={`fixed bottom-6 right-6 p-4 rounded-full shadow-2xl transition-all duration-500 z-50 flex items-center justify-center border-4 border-white ${showAi ? 'bg-red-500 rotate-90' : 'bg-slate-900 hover:scale-110 active:scale-95'}`}
            >
                {showAi ? <X size={24} className="text-white" /> : <Bot size={28} className="text-white animate-bounce-subtle" />}
            </button>

            {/* AI Chat Window with Premium Animations */}
            {showAi && (
                <div className="fixed bottom-24 right-6 w-80 bg-white/95 backdrop-blur-xl rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.2)] border border-white/20 z-50 p-4 animate-in fade-in slide-in-from-bottom-10 zoom-in-95 duration-300 origin-bottom-right">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-100">
                        <div className="bg-emerald-100 p-1.5 rounded-lg"><Sparkles className="text-emerald-600 w-4 h-4 animate-spin-slow" /></div>
                        <span className="font-bold text-sm text-slate-800 tracking-tight">小J 智慧管家</span>
                        <div className="ml-auto flex gap-1">
                            <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                            <span className="text-[10px] text-slate-400">連線中</span>
                        </div>
                    </div>
                    <div className="h-64 bg-slate-50/50 rounded-xl p-4 text-xs text-slate-600 overflow-y-auto mb-3 custom-scrollbar">
                        <div className="flex gap-2 mb-4 animate-in fade-in slide-in-from-left-2 duration-500">
                            <div className="w-9 h-9 rounded-full bg-slate-900 text-white flex-shrink-0 flex items-center justify-center font-bold shadow-lg">J</div>
                            <div className="bg-white p-3 rounded-2xl rounded-tl-none shadow-sm border border-slate-100 relative group overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-r from-emerald-50/0 via-emerald-50/30 to-emerald-50/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                                <p className="font-bold mb-1 text-slate-800">江大哥您好！</p>
                                <p className="leading-relaxed">我是小J。目前您的「提案補助金」餘額充足，是否要前往許願樹投票？✨</p>
                            </div>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button className="p-2.5 bg-slate-100 rounded-xl hover:bg-slate-200 transition-all text-slate-600 active:scale-90"><Mic size={18} /></button>
                        <input className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-xs outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all" placeholder="想跟小J說什麼？" />
                        <button className="bg-slate-900 text-white p-2.5 rounded-xl hover:bg-slate-800 transition-all active:scale-90 shadow-lg"><Send size={18} /></button>
                    </div>
                </div>
            )}
        </div>
    );
}
