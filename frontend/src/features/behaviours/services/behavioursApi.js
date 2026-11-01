import { listBehaviours } from '../api';
export async function fetchBehaviours() {
    const data = await listBehaviours();
    return data.items;
}
