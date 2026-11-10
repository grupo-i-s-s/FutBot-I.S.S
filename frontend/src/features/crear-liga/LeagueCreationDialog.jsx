import {ArrowLeft, X} from 'lucide-react';
import {useNavigate} from 'react-router';
import {Button} from '@/components/ui/button';
import {Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {routes} from '@/routes.js';

export default function LeagueCreationDialog({title, description, icon: Icon, busy, children}) {
    const navigate = useNavigate();
    const close = () => navigate(routes.home, {replace: true});

    return (
        <Dialog open onOpenChange={open => { if (!open && !busy) close(); }}>
            <DialogContent showCloseButton={false} className="max-h-[90dvh] overflow-y-auto rounded-2xl p-6 sm:max-w-2xl" aria-busy={busy}>
                <div className="flex items-center justify-between gap-3">
                    <Button type="button" variant="ghost" disabled={busy} onClick={close}>
                        <ArrowLeft aria-hidden="true"/> Volver al inicio
                    </Button>
                    <DialogClose render={<Button type="button" variant="ghost" size="icon" disabled={busy}/>}>
                        <X aria-hidden="true"/><span className="sr-only">Cerrar</span>
                    </DialogClose>
                </div>
                <DialogHeader className="gap-3 border-b pb-5">
                    <div className="flex items-center gap-3">
                        <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
                            <Icon className="size-6" aria-hidden="true"/>
                        </span>
                        <DialogTitle className="text-2xl leading-tight font-bold tracking-tight">{title}</DialogTitle>
                    </div>
                    <DialogDescription>{description}</DialogDescription>
                </DialogHeader>
                {children}
            </DialogContent>
        </Dialog>
    );
}
