const puppeteer = require('puppeteer');

(async () => {
  try {
    console.log('Launching browser...');
    const browser = await puppeteer.launch({
      executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
      headless: true
    });
    const page = await browser.newPage();
    
    // Set viewport for a standard A4-like experience
    await page.setViewport({ width: 794, height: 1122, deviceScaleFactor: 2 });
    
    console.log('Loading page...');
    await page.goto('file:///C:/Users/pc%20gamer/Documents/desktopapp/cv.html', {
      waitUntil: 'networkidle0',
    });
    
    console.log('Generating PDF...');
    await page.pdf({ 
      path: 'C:/Users/pc gamer/Documents/desktopapp/CV_Grir_Saif_Elislam.pdf', 
      format: 'A4', 
      printBackground: true,
      margin: {
        top: '0px',
        bottom: '0px',
        left: '0px',
        right: '0px'
      }
    });
    
    await browser.close();
    console.log('PDF generated successfully!');
  } catch (err) {
    console.error('Error generating PDF:', err);
    process.exit(1);
  }
})();
