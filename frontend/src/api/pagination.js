export async function listAllPages(fetchPage) {
    const items = new Map();
    let page = 1;

    while (true) {
        const response = await fetchPage(page);
        for (const item of response.items) items.set(item.id, item);

        if (!response.hasNext) return [...items.values()];
        page += 1;
    }
}
