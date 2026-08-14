import http from 'k6/http';
import { check, sleep, group } from 'k6';

export let options = {
    stages: [
        { duration: '30s', target: 300 }, // Ramp up to 300 users
        { duration: '1m', target: 300 },  // Hold 300 users
        { duration: '30s', target: 0 },    // Ramp down to 0 users
    ],
    thresholds: {
        'http_req_duration': ['p(95)<500'], // 95th percentile response time must be below 500ms
    },
};

const BASE_URL = 'http://localhost:5000';

const journeys = [
    {
        name: "Buyer Journey",
        flow: ["/login", "/products", "/search", "/product", "/cart", "/checkout", "/payment"]
    },
    {
        name: "Guest Journey",
        flow: ["/homepage", "/products", "/search", "/exit"]
    },
    {
        name: "Returning Customer",
        flow: ["/login", "/orders", "/track-order", "/logout"]
    },
    {
        name: "Checkout Journey",
        flow: ["/login", "/products", "/cart", "/checkout", "/cancel-order", "/logout"]
    },
    {
        name: "Other",
        flow: ["/login", "/products", "/search"]
    }
];

export default function () {
    const journey = journeys[Math.floor(Math.random() * journeys.length)];
    
    group(journey.name, function () {
        journey.flow.forEach((endpoint) => {
            const res = http.get(`${BASE_URL}${endpoint}`);
            check(res, {
                'is status 200': (r) => r.status === 200,
                'response time is < 500ms': (r) => r.timings.duration < 500,
            });
            sleep(1); // Sleep for 1 second between requests
        });
    });
}