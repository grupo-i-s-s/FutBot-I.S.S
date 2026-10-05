import {request} from "@/api/http.js";

export async function getFriendlyMatches(){
    return request('/friendly-matches')
}