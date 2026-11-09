import {Card, CardContent, CardDescription, CardFooter, CardHeader} from '@/components/ui/card';

export default function AuthCard({icon: Icon, title, description, children, footer}) {
    return (
        <main className="mx-auto flex w-[calc(100%_-_32px)] max-w-md flex-1 flex-col justify-center py-8 sm:py-12">
            <Card className="shadow-sm [--card-spacing:--spacing(5)] sm:[--card-spacing:--spacing(6)]">
                <CardHeader className="grid-cols-[auto_minmax(0,1fr)] items-center gap-x-4 gap-y-1 border-b">
                    <p className="col-start-2 row-start-1 text-xs font-bold tracking-[0.12em] text-primary uppercase">
                        FutBot
                    </p>
                    <span className="col-start-1 row-start-2 grid size-12 place-items-center rounded-xl bg-primary/10 text-primary">
                        <Icon className="size-6" aria-hidden="true"/>
                    </span>
                    <h1 className="col-start-2 row-start-2 text-xl font-bold leading-tight sm:text-2xl">{title}</h1>
                    {description && (
                        <CardDescription className="col-start-2 row-start-3 wrap-anywhere">{description}</CardDescription>
                    )}
                </CardHeader>

                {children && <CardContent>{children}</CardContent>}

                {footer && <CardFooter className="justify-center text-center">{footer}</CardFooter>}
            </Card>
        </main>
    );
}
