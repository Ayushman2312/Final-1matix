
  // FAQ data organized by category
  const faqData = {
    'service': [
      {
        question: 'What services do you offer?',
        answer: 'We offer a wide range of services including financial planning, investment management, and retirement planning.'
      },
      {
        question: 'How do I request a specific service?',
        answer: 'You can request a service by filling out our contact form or calling our customer service number.'
      },
      {
        question: 'Are your services available internationally?',
        answer: 'Yes, many of our services are available internationally. Please contact us for specific availability in your region.'
      }
    ],
    'plans': [
      {
        question: 'What plans do you offer?',
        answer: 'We offer Basic, Premium, and Enterprise plans to suit different needs and budgets.'
      },
      {
        question: 'Can I upgrade my plan later?',
        answer: 'Yes, you can upgrade your plan at any time. The new pricing will be prorated for the remainder of your billing cycle.'
      },
      {
        question: 'Do you offer custom plans?',
        answer: 'Yes, we offer custom plans for businesses with specific requirements. Please contact our sales team for more information.'
      }
    ],
    'refunds': [
      {
        question: 'What is your refund policy?',
        answer: 'We offer a 30-day money-back guarantee for all our services. If you are not satisfied, you can request a full refund within this period.'
      },
      {
        question: 'How do I request a refund?',
        answer: 'To request a refund, please contact our customer support team with your order details.'
      },
      {
        question: 'How long does the refund process take?',
        answer: 'Refunds are typically processed within 5-7 business days, depending on your payment method and financial institution.'
      }
    ],
    'manage': [
      {
        question: 'How do I manage my account?',
        answer: 'You can manage your account through our online dashboard. Log in to access all account settings and preferences.'
      },
      {
        question: 'Can I change my payment method?',
        answer: 'Yes, you can update your payment method at any time through the account settings page.'
      },
      {
        question: 'How do I cancel my subscription?',
        answer: 'You can cancel your subscription through the account settings page. Your access will continue until the end of your current billing period.'
      }
    ]
  };

  // Function to create FAQ accordion item
  function createFAQItem(question, answer) {
    const faqItem = document.createElement('div');
    faqItem.className = 'bg-white rounded-xl p-6 border border-gray-100 shadow-sm';
    
    const questionDiv = document.createElement('div');
    questionDiv.className = 'flex justify-between items-center cursor-pointer';
    questionDiv.innerHTML = `
      <h4 class="font-medium">${question}</h4>
      <svg class="w-5 h-5 transform transition-transform duration-300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 9l6 6 6-6"/>
      </svg>
    `;
    
    const answerDiv = document.createElement('div');
    answerDiv.className = 'mt-4 text-gray-600 hidden transition-all duration-300 ease-in-out';
    answerDiv.textContent = answer;
    
    questionDiv.addEventListener('click', () => {
      const isOpen = answerDiv.classList.contains('hidden');
      const allAnswers = document.querySelectorAll('#faqAccordion > div > div:last-child');
      const allArrows = document.querySelectorAll('#faqAccordion > div > div:first-child svg');
      
      // Close all other answers
      allAnswers.forEach(ans => {
        ans.classList.add('hidden');
        ans.style.maxHeight = '0';
      });
      allArrows.forEach(arrow => arrow.classList.remove('rotate-180'));
      
      // Toggle current answer
      if (isOpen) {
        answerDiv.classList.remove('hidden');
        answerDiv.style.maxHeight = answerDiv.scrollHeight + 'px';
        questionDiv.querySelector('svg').classList.add('rotate-180');
      } else {
        answerDiv.classList.add('hidden');
        answerDiv.style.maxHeight = '0';
        questionDiv.querySelector('svg').classList.remove('rotate-180');
      }
    });
    
    faqItem.appendChild(questionDiv);
    faqItem.appendChild(answerDiv);
    return faqItem;
  }

  // Function to update FAQ content
  function updateFAQContent(category) {
    console.log('Updating FAQ content for category:', category);
    const faqContainer = document.getElementById('faqAccordion');
    const categoryTitle = document.getElementById('faqCategoryTitle');
    
    if (!faqContainer || !categoryTitle) {
      console.error('Required elements not found');
      return;
    }
    
    // Update category title
    categoryTitle.textContent = category.charAt(0).toUpperCase() + category.slice(1);
    
    // Clear existing FAQ items
    faqContainer.innerHTML = '';
    
    // Add new FAQ items
    if (faqData[category]) {
      faqData[category].forEach(item => {
        const faqItem = createFAQItem(item.question, item.answer);
        faqContainer.appendChild(faqItem);
      });
    } else {
      console.error('Category not found in faqData:', category);
    }
  }

  // Initialize FAQ functionality
  document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing FAQ functionality');
    
    // Add click event listeners to category cards
    const categoryCards = document.querySelectorAll('.faq-category');
    console.log('Found category cards:', categoryCards.length);
    
    categoryCards.forEach(card => {
      card.addEventListener('click', function() {
        const category = this.dataset.category;
        console.log('Category clicked:', category);
        
        // Remove active class from all cards
        categoryCards.forEach(c => {
          c.classList.remove('border-black', 'bg-gray-50');
        });
        
        // Add active class to clicked card
        this.classList.add('border-black', 'bg-gray-50');
        
        // Update FAQ content
        updateFAQContent(category);
      });
    });

    // Set Service category as active by default
    const defaultCategory = document.querySelector('.faq-category[data-category="service"]');
    if (defaultCategory) {
      defaultCategory.classList.add('border-black', 'bg-gray-50');
      updateFAQContent('service');
    }
  });