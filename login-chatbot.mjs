export default async function run(page, ui) {
  // Wait for login form
  await page.waitForSelector('#email', { timeout: 10000 });
  
  // Fill login form
  await page.fill('#email', 'test3@gmail.com');
  await page.fill('#password', '123456');
  
  // Select paciente role
  const pacienteRole = await page.$('[data-role="paciente"]');
  if (pacienteRole) {
    await pacienteRole.click();
  }
  
  // Click login
  await page.click('button[type="submit"]');
  
  // Wait for navigation to dashboard
  await page.waitForTimeout(5000);
  
  // Navigate to chatbot page
  await page.goto('http://127.0.0.1:8000/aside-patient/chatbot.html');
  await page.waitForTimeout(3000);
  
  // Take screenshot
  await page.screenshot({ path: 'chatbot-authenticated.png' });
  
  // Get page content
  const content = await page.content();
  return { 
    url: page.url(),
    title: await page.title(),
    hasChatArea: content.includes('chat-area'),
    contentLength: content.length
  };
}