
"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "./ui/dialog";
import { Button } from "./ui/button";
import { Upload, FileJson, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";

interface ImportJSONModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onImportSuccess: (sourceId: string) => void;
    accessToken?: string;
}

export function ImportJSONModal({ open, onOpenChange, onImportSuccess, accessToken }: ImportJSONModalProps) {
    const [file, setFile] = useState<File | null>(null);
    const [name, setName] = useState("");
    const [status, setStatus] = useState<'idle' | 'uploading' | 'processing' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState("");

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            if (!name) {
                // Default name from filename
                setName(selectedFile.name.replace('.json', ''));
            }
        }
    };

    const handleImport = async () => {
        if (!file || !name) return;

        setStatus('uploading');
        try {
            const res = await api.importCatalog(file, name, accessToken);
            setStatus('success');
            setMessage(res.message);
            setTimeout(() => {
                onImportSuccess(res.source_id);
                onOpenChange(false);
                // Reset
                setFile(null);
                setName("");
                setStatus('idle');
            }, 2000);
        } catch (err: unknown) {
            setStatus('error');
            setMessage(err instanceof Error ? err.message : "Ошибка при импорте");
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Импорт каталога JSON</DialogTitle>
                    <DialogDescription>
                        Загрузите файл с товарами, чтобы добавить новый источник.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    {status === 'idle' || status === 'error' ? (
                        <>
                            <div className="flex flex-col gap-2">
                                <label className="text-sm font-medium text-muted-foreground">Название источника</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="Например: Моя коллекция"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                />
                            </div>

                            <div className="flex flex-col gap-2">
                                <label className="text-sm font-medium text-muted-foreground">Файл JSON</label>
                                <div
                                    className="border-2 border-dashed border-muted rounded-xl p-8 flex flex-col items-center justify-center gap-3 bg-secondary/10 hover:bg-secondary/20 transition-colors cursor-pointer relative"
                                    onClick={() => document.getElementById('json-upload')?.click()}
                                >
                                    <input
                                        id="json-upload"
                                        type="file"
                                        accept=".json"
                                        className="hidden"
                                        onChange={handleFileChange}
                                    />
                                    {file ? (
                                        <>
                                            <FileJson className="h-10 w-10 text-[#c6613f]" />
                                            <span className="text-sm font-medium text-[#141413]">{file.name}</span>
                                        </>
                                    ) : (
                                        <>
                                            <Upload className="h-10 w-10 text-muted-foreground/50" />
                                            <span className="text-sm text-muted-foreground">Нажмите, чтобы выбрать файл</span>
                                        </>
                                    )}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-8 gap-4 text-center">
                            {status === 'uploading' || status === 'processing' ? (
                                <>
                                    <Loader2 className="h-12 w-12 text-[#c6613f] animate-spin" />
                                    <div className="space-y-1">
                                        <p className="font-medium text-[#141413]">
                                            {status === 'uploading' ? 'Загрузка файла...' : 'Обработка и переиндексация...'}
                                        </p>
                                        <p className="text-xs text-muted-foreground">Это может занять до минуты</p>
                                    </div>
                                </>
                            ) : status === 'success' ? (
                                <>
                                    <CheckCircle2 className="h-12 w-12 text-green-500" />
                                    <p className="font-medium text-[#141413]">{message}</p>
                                </>
                            ) : null}
                        </div>
                    )}

                    {status === 'error' && (
                        <div className="flex items-center gap-2 text-destructive text-sm bg-destructive/10 p-3 rounded-lg">
                            <AlertCircle className="h-4 w-4" />
                            <span>{message}</span>
                        </div>
                    )}
                </div>

                {status === 'idle' || status === 'error' ? (
                    <DialogFooter>
                        <Button variant="outline" onClick={() => onOpenChange(false)}>Отмена</Button>
                        <Button
                            className="bg-[#c6613f] hover:bg-[#a54f32] text-white"
                            disabled={!file || !name}
                            onClick={handleImport}
                        >
                            Импортировать
                        </Button>
                    </DialogFooter>
                ) : null}
            </DialogContent>
        </Dialog>
    );
}
